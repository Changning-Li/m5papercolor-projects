#!/usr/bin/env python3
"""Fast host-side regression checks for PaperColor project invariants.

These checks deliberately avoid hardware access.  They protect the configuration
and call-order mistakes that previously made NTP/RTC and the header layout lie to
the user; the final PlatformIO build still verifies the embedded code itself.
"""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = ROOT.parents[1]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def read_workspace(relative_path: str) -> str:
    return (WORKSPACE_ROOT / relative_path).read_text(encoding="utf-8")


class TimekeepingRegressionTests(unittest.TestCase):
    def test_network_time_is_not_overwritten_by_build_time(self) -> None:
        source = read("src/main.cpp")
        self.assertRegex(source, r"#define\s+FORCE_RTC_SYNC\s+0\b")
        self.assertRegex(source, r"bool\s+ntpSynced\s*=\s*tryNTPSync\(\)")
        self.assertRegex(
            source,
            r"if\s*\(\s*!ntpSynced\s*\)\s*\{\s*ensureRTCTime\(forceSync\)",
        )

    def test_raw_rx8130_uses_the_same_vlf_register_as_m5unified(self) -> None:
        source = read("src/rx8130_rtc.h")
        self.assertRegex(source, r"RX8130_REG_FLAG\s+0x1D")
        self.assertRegex(source, r"RX8130_FLAG_VLF\s+0x80")
        self.assertNotRegex(source, r"readRegister\([^\n]*0x1E[^\n]*flag")

    def test_startup_report_window_begins_after_setup(self) -> None:
        source = read("src/main.cpp")
        self.assertIn("startupReportStart = millis();", source)
        self.assertIn("now - startupReportStart", source)
        self.assertNotIn("if (millis() > 20000)", source)

    def test_sampling_deadline_is_measured_after_blocking_epd_refresh(self) -> None:
        source = read("src/main.cpp")
        self.assertNotIn("lastSample = now;", source)
        self.assertGreaterEqual(source.count("lastSample = millis();"), 3)


class LayoutRegressionTests(unittest.TestCase):
    def test_header_status_is_on_the_shortened_subtitle_row(self) -> None:
        source = read("src/env_ui.h")
        self.assertIn('"SHT40 | RX8130 | 4in E-Ink"', source)
        self.assertRegex(source, r"int\s+cy\s*=\s*UI_HEAD_H\s*-\s*16")

    def test_environment_cards_are_above_time_and_battery(self) -> None:
        source = read("src/env_ui.h")
        for call in (
            "drawTempCard(UI_CARD_L, UI_ROW1_Y, data);",
            "drawHumiCard(UI_CARD_R, UI_ROW1_Y, data);",
            "drawTimeCard(UI_CARD_L, UI_ROW2_Y, data);",
            "drawBatteryCard(UI_CARD_R, UI_ROW2_Y, data);",
        ):
            self.assertIn(call, source)


class ProjectHygieneTests(unittest.TestCase):
    def test_dependencies_are_version_pinned(self) -> None:
        config = read("platformio.ini")
        self.assertNotIn("https://github.com/m5stack/", config)
        for dependency in (
            "m5stack/M5Unified @ 0.2.21",
            "m5stack/M5GFX @ 0.2.28",
            "m5stack/M5PM1 @ 1.0.7",
            "robtillaart/SHT4x @ 0.1.2",
        ):
            self.assertIn(dependency, config)

    def test_local_secrets_and_generated_files_are_ignored(self) -> None:
        ignore = read_workspace(".gitignore")
        for entry in (".pio/", ".DS_Store", "src/secrets.h", "*.bak"):
            self.assertIn(entry, ignore)
        self.assertIn('#include "secrets.h"', read("src/main.cpp"))

    def test_readme_describes_the_current_refresh_policy(self) -> None:
        readme = read("README.md")
        self.assertIn("每 15 秒采样", readme)
        self.assertIn("每 5 分钟", readme)
        self.assertNotIn("60 秒自动刷新", readme)


if __name__ == "__main__":
    unittest.main()
