"""Nghiệm thu VAD trên PCM16 gốc từ manifest đã được freeze của 02_Quality_Check.

plan      : chỉ đọc QC manifest và WAV header, TUYỆT ĐỐI không đọc PCM Test.
calibrate : đọc duy nhất Calibration PCM, sinh chunk MAV để notebook sweep.
test      : chỉ đọc Test PCM sau khi đã freeze cấu hình VAD bằng Calibration.

Dùng nguyên WAV Environment master (không cắt 5s), Playback nguyên WAV thu qua
INMP441. Với Playback giả định Node đã sẵn sàng LISTENING trước khi phát; warmup
đã kết thúc trước file, 1 giây đầu làm đầy ring. Từ 1 giây không được coi là
ground-truth acoustic onset nếu chưa có nhãn thời gian độc lập.
"""
from __future__ import annotations
import argparse
import csv
import json
from collections import Counter,defaultdict
from pathlib import Path
import sys
import wave
import numpy as np
from vad_utils import (SAMPLE_RATE, VadConfig, pcm16_chunk_mav,
                       simulate, sha256, load_frozen)

for stream in (sys.stdout,sys.stderr):
    if hasattr(stream,'reconfigure'):
        stream.reconfigure(encoding='utf-8',errors='replace')
HERE=Path(__file__).resolve().parent
QC_DIR=HERE.parent/'02_Quality_Check'
QC_MANIFEST=QC_DIR/'results'/'quality_window_manifest.csv'
QC_FREEZE=QC_DIR/'results'/'final_quality_gate.json'
OUT=HERE/'results'
MANIFEST=OUT/'vad_source_manifest.csv'
CAL_META=OUT/'calibration_source_metrics.csv'
CAL_NPZ=OUT/'calibration_chunk_mav.npz'
FINAL=OUT/'final_vad_trigger.json'
TEST_META=OUT/'test_source_metrics.csv'
TEST_NPZ=OUT/'test_chunk_mav.npz'
TEST_EVENTS=OUT/'test_trigger_events.csv'

COLUMNS=['vad_split','original_split','source_kind','subtype','session_id','source_group',
         'file_path','file_name','nframes','duration_s','playback_prearmed']
METADATA=COLUMNS+['chunk_key','num_chunks','min_chunk_mav','median_chunk_mav',
                  'p95_chunk_mav','max_chunk_mav']
EVENT_COLS=['source_group','file_name','subtype','source_kind','event_no','candidate_onset_s',
            'confirmed_s','confirmation_delay_ms','recovered_samples','recovered_ms',
            'confirm_mav','capture_complete','capture_end_s']


def csv_read(path: Path)->list[dict]:
    with path.open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))


def csv_save(path: Path, rows: list[dict], columns: list[str]):
    if path.exists():
        raise FileExistsError(f'Đã có {path}, hãy lưu trữ lần chạy trước, không ghi đè')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=columns,extrasaction='ignore')
        w.writeheader();w.writerows(rows)


def inspect_header(path: Path):
    with wave.open(str(path),'rb') as wf:
        if (wf.getnchannels(),wf.getsampwidth(),wf.getframerate(),wf.getcomptype()) != (1,2,16000,'NONE'):
            raise ValueError(f'WAV phải là PCM16 mono 16kHz: {path}')
        return wf.getnframes()


def check_qc_frozen(qc_manifest: Path, qc_freeze: Path):
    if not qc_freeze.exists():
        raise FileNotFoundError(f'Chưa có Quality Gate FROZEN: {qc_freeze}')
    cfg=json.loads(qc_freeze.read_text(encoding='utf-8'))
    if cfg.get('status')!='FROZEN' or cfg.get('manifest_sha256') != sha256(qc_manifest):
        raise ValueError('Manifest Quality không trùng manifest đã FROZEN; phải kiểm tra lại nguồn')


def make_plan(qc_manifest: Path, qc_freeze: Path):
    if MANIFEST.exists():
        raise FileExistsError(f'Manifest VAD đã tồn tại: {MANIFEST}')
    check_qc_frozen(qc_manifest,qc_freeze)
    qc=csv_read(qc_manifest)
    if not qc:raise ValueError('QC manifest rỗng')
    uniques={}; splits=defaultdict(set); source_files=defaultdict(set)
    for x in qc:
        split=x['qc_split'].strip().lower()
        if split not in ('calibration','test'):
            raise ValueError('Invalid QC split: '+split)
        source=x['source_group'];p=str(Path(x['file_path']).resolve())
        splits[source].add(split)
        source_files[source].add(p)
        key=(source,p)
        if key not in uniques:
            uniques[key]=x
        else:
            if x['subtype']!=uniques[key]['subtype'] or x['qc_split']!=uniques[key]['qc_split']:
                raise ValueError(f'Inconsistent QC manifest: {key}')
    leaked={k:v for k,v in splits.items() if len(v)>1}
    if leaked:raise ValueError('Leakage giữa Calibration/Test: '+str(leaked))
    env_sources={k for k,p in source_files.items() if k.startswith(('podcast_','fan_','clap_','knock_','room_noise_','speech_'))}
    # Bao gồm podcast_old_01 trong 33 chính; không gồm keyfan/silence.
    if len(env_sources)!=33:
        raise ValueError(f'Cần 33 Environment chính (có podcast_old_01), nhận {len(env_sources)}. QC manifest có thể là bản cũ.')
    for sid in ('silence_old_01','keyfan_old_01'):
        if sid not in source_files or splits[sid]!={'calibration'}:
            raise ValueError(f'Legacy asset thiếu/sai split: {sid}')
    env_test={k for k in env_sources if splits[k]=={'test'}}
    if len(env_test)!=3:
        raise ValueError(f'Test Environment theo V2 cần 3 session, nhận {sorted(env_test)}')

    rows=[]
    for (source,path_str),x in sorted(uniques.items()):
        path=Path(path_str)
        if not path.exists():raise FileNotFoundError(path)
        n=inspect_header(path)
        if n < SAMPLE_RATE:
            raise ValueError('WAV quá ngắn để tạo 1 giây ring: '+str(path))
        rows.append({
            'vad_split':x['qc_split'],'original_split':x['original_split'],
            'source_kind':x['source_kind'],'subtype':x['subtype'],
            'session_id':x['session_id'],'source_group':source,
            'file_path':str(path),'file_name':path.name,'nframes':n,
            'duration_s':f'{n/SAMPLE_RATE:.6f}',
            'playback_prearmed':int(x['source_kind']=='playback')})
    csv_save(MANIFEST,rows,COLUMNS)
    print(f'PLAN OK: {len(rows)} WAV gốc; {len(source_files)} nhóm nguồn.')
    print('WAV theo split:',dict(Counter(x['vad_split'] for x in rows)))
    print('Session Environment Test:',sorted(env_test))
    print('Chưa đọc PCM Test; chỉ kiểm tra WAV header.')


def load_pcm(path:Path)->np.ndarray:
    with wave.open(str(path),'rb') as wf:
        if (wf.getnchannels(),wf.getsampwidth(),wf.getframerate(),wf.getcomptype())!=(1,2,16000,'NONE'):
            raise ValueError('Không đúng PCM16 mono 16kHz: '+str(path))
        data=wf.readframes(wf.getnframes())
    return np.frombuffer(data,dtype='<i2').copy()


def extract_split(stage:str):
    if not MANIFEST.exists():raise FileNotFoundError('Chưa plan: '+str(MANIFEST))
    meta, chunk_file=(CAL_META,CAL_NPZ) if stage=='calibration' else (TEST_META,TEST_NPZ)
    if meta.exists() or chunk_file.exists():
        raise FileExistsError('Output đã tồn tại, không ghi đè: '+str(meta))
    cfg=None
    if stage=='test':
        cfg,_=load_frozen(FINAL,MANIFEST,CAL_META,CAL_NPZ)
        if TEST_EVENTS.exists():raise FileExistsError('Events Test đã tồn tại')
    rows=[r for r in csv_read(MANIFEST) if r['vad_split']==stage]
    if not rows:raise ValueError('Split rỗng: '+stage)
    arrays={}; metadata=[]; all_events=[]
    for i,row in enumerate(rows):
        pcm=load_pcm(Path(row['file_path']))
        if len(pcm)!=int(row['nframes']):
            raise ValueError('WAV thay đổi kể từ plan: '+row['file_path'])
        mav,lengths=pcm16_chunk_mav(pcm)
        key=f'source_{i:04d}'
        arrays[key+'_mav']=mav
        arrays[key+'_len']=lengths
        metadata.append({**row, 'chunk_key':key,'num_chunks':len(mav),
                         'min_chunk_mav':int(mav.min()),
                         'median_chunk_mav':float(np.median(mav)),
                         'p95_chunk_mav':float(np.percentile(mav,95)),
                         'max_chunk_mav':int(mav.max())})
        if stage=='test':
            events=simulate(mav,lengths,cfg,playback_prearmed=row['playback_prearmed']=='1')
            for j,ev in enumerate(events,1):
                all_events.append({**{k:row[k] for k in ('source_group','file_name','subtype','source_kind')},
                                   'event_no':j,**ev})
    chunk_file.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(chunk_file,**arrays)
    csv_save(meta,metadata,METADATA)
    if stage=='test':
        csv_save(TEST_EVENTS,all_events,EVENT_COLS)
    print(f'{stage.upper()}: {len(rows)} nguồn -> {meta.name}, {chunk_file.name}')
    if stage=='test':
        print('Test trigger events:',len(all_events),'| complete:',sum(e['capture_complete'] for e in all_events))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=['plan','calibrate','test'])
    p.add_argument('--qc-manifest',type=Path,default=QC_MANIFEST)
    p.add_argument('--qc-freeze',type=Path,default=QC_FREEZE)
    args=p.parse_args()
    if args.stage=='plan':make_plan(args.qc_manifest,args.qc_freeze)
    else:extract_split('calibration' if args.stage=='calibrate' else 'test')

if __name__=='__main__':main()
