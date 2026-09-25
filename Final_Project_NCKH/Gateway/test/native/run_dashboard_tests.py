from pathlib import Path
import subprocess, tempfile, json
root=Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory() as tmp:
 for mode in [0,2]:
  exe=str(Path(tmp)/'dashboard.exe')
  subprocess.check_call(['g++','-std=c++11','-Wall','-Wextra','-Werror',f'-DGATEWAY_SENSOR_MODE={mode}','-Itest/native','-Iinclude','test/native/test_dashboard.cpp','src/gateway_json.cpp','-o',exe],cwd=root)
  rows=[json.loads(s) for s in subprocess.check_output([exe],text=True).splitlines()]
  assert all(x['schema_version']==2 and x['message_type']=='dashboard_snapshot' for x in rows)
  assert all(x['synthetic']==(mode==2) for x in rows)
  assert rows[0]['patient_event'] is None and rows[0]['event_id'] is None
  assert not rows[0]['alert']['active'] and not rows[0]['status']['node_valid']
  assert rows[1]['patient_event']==rows[2]['patient_event']
  assert rows[1]['event_id']==rows[2]['event_id']==rows[1]['alert']['event_id']
  assert rows[1]['record_id']!=rows[2]['record_id']
  assert rows[1]['patient_age_ms']==1000 and rows[2]['patient_age_ms']==6000
  assert rows[1]['status']['node_dirty'] and not rows[2]['status']['node_dirty']
  assert not rows[3]['alert']['active'] and rows[3]['patient_event']['heart_rate'] is None
  assert not rows[4]['alert']['active'] and rows[5]['alert']['active']
  assert rows[6]['patient_age_ms'] is None
  print(f'PASS dashboard mode={mode}: missing/clean/dirty/age/event ID/alert threshold/nulls/buffer bounds')
  if mode==0:
   (root/'test/native/dashboard_example.json').write_text(json.dumps(rows[1],indent=2)+'\n')
