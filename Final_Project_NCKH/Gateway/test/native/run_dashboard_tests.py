from pathlib import Path
import json
import subprocess
import tempfile


root = Path(__file__).resolve().parents[2]

with tempfile.TemporaryDirectory() as tmp:
    for mode in [0, 2]:
        # Dùng file riêng cho từng mode để tránh Windows còn giữ handle của
        # executable vừa chạy khi linker chuẩn bị ghi đè vòng kế tiếp.
        exe = str(Path(tmp) / f"dashboard_{mode}.exe")
        subprocess.check_call(
            [
                "g++",
                "-std=c++11",
                "-Wall",
                "-Wextra",
                "-Werror",
                f"-DGATEWAY_SENSOR_MODE={mode}",
                "-Itest/native",
                "-Iinclude",
                "test/native/test_dashboard.cpp",
                "src/gateway_json.cpp",
                "-o",
                exe,
            ],
            cwd=root,
        )
        rows = [
            json.loads(line)
            for line in subprocess.check_output([exe], text=True).splitlines()
        ]

        assert all(
            row["schema_version"] == 1
            and row["message_type"] == "complete_packet"
            for row in rows
        )
        assert all(row["synthetic"] == (mode == 2) for row in rows)

        # Chưa có Node: chỉ gửi Gateway.
        assert rows[0]["patient_event"] is None
        assert rows[0]["event_id"] is None
        assert not rows[0]["alert"]["active"]
        assert not rows[0]["status"]["node_valid"]

        # Retry Event A: Event ID giữ nguyên, Record ID thay đổi.
        assert rows[1]["has_patient_event"]
        assert rows[1]["patient_event"] == rows[2]["patient_event"]
        assert rows[1]["event_id"] == rows[2]["event_id"]
        assert rows[1]["record_id"] != rows[2]["record_id"]
        assert rows[1]["patient_age_ms"] == 1000
        assert rows[2]["patient_age_ms"] == 3000
        assert rows[1]["alert"]["active"] and rows[2]["alert"]["active"]
        assert rows[1]["patient_event"]["battery_node"] is None

        # Publish thành công: vẫn còn Node cục bộ nhưng Complete Packet không gửi lặp Event.
        assert not rows[3]["has_patient_event"]
        assert rows[3]["patient_event"] is None
        assert rows[3]["event_id"] is None
        assert rows[3]["patient_age_ms"] is None
        assert rows[3]["status"]["node_valid"]
        assert not rows[3]["status"]["node_dirty"]

        # Chỉ ASTHMA (0) đạt ngưỡng mới cảnh báo; NON-ASTHMA/UNSURE không cảnh báo.
        assert not rows[4]["alert"]["active"]
        assert rows[4]["patient_event"]["heart_rate"] is None
        assert rows[4]["patient_event"]["spo2"] is None
        assert not rows[5]["alert"]["active"]
        assert not rows[6]["alert"]["active"]
        assert rows[7]["alert"]["active"]

        assert rows[8]["patient_age_ms"] is None

        print(
            f"PASS dashboard mode={mode}: schema1/complete_packet/dirty-only/"
            "retry/event ID/classification/null/buffer bounds"
        )
        if mode == 0:
            (root / "test/native/dashboard_example.json").write_text(
                json.dumps(rows[1], indent=2) + "\n",
                encoding="utf-8",
            )
