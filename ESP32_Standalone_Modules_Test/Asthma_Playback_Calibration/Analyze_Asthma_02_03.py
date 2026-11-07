"""Chay tron bo offset + shifted-original cho hai Asthma file 02 va 03.

Khong can ESP32: script chi doc calibration CSV va cac capture da luu.
"""

from __future__ import annotations

import sys

try:
    from . import Analyze_Capture_Offset as offset_analysis
    from . import Analyze_Shifted_Original_vs_Capture as shift_analysis
    from .Run_Playback_Calibration import PythonV1Runner
except ImportError:
    import Analyze_Capture_Offset as offset_analysis
    import Analyze_Shifted_Original_vs_Capture as shift_analysis
    from Run_Playback_Calibration import PythonV1Runner


TARGET_FILES = [
    "Playback_Calibration/Asthma/02__P17WheezingIE_85.wav",
    "Playback_Calibration/Asthma/03__P47WheezingRL_235.wav",
]


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 72)
    print("ASTHMA 02 + 03: OFFSET -> SHIFTED ORIGINAL VS CAPTURE")
    print("=" * 72)

    print("\n[PHASE 1] Do cross-correlation va offset")
    for target_file in TARGET_FILES:
        print("\n" + "-" * 72)
        print(f"Target: {target_file}")
        offset_analysis.analyze_target(target_file)

    print("\n[PHASE 2] Tai Python preprocessing + V1 PTQ INT8 mot lan")
    runner = PythonV1Runner()

    print("\n[PHASE 3] Crop shifted-original va so voi capture")
    for target_file in TARGET_FILES:
        print("\n" + "-" * 72)
        print(f"Target: {target_file}")
        shift_analysis.analyze_target(target_file, runner=runner)

    print("\n" + "=" * 72)
    print("DA HOAN THANH ASTHMA FILE 02 VA 03")
    print("Ket qua nam trong calibration_results/offset_analysis/<ten_file>/")


if __name__ == "__main__":
    main()
