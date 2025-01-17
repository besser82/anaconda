#
# Copyright (C) 2013  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.
#

from pyanaconda import localization
from pyanaconda.core.constants import DEFAULT_LANG
from pyanaconda.core.util import execWithCapture
import locale as locale_mod
import unittest
from unittest.mock import call, patch, MagicMock
from io import StringIO

# pylint: disable=environment-modify
# required due to mocking os.environ

class LangcodeLocaleParsingTests(unittest.TestCase):

    def tearDown(self):
        locale_mod.setlocale(locale_mod.LC_ALL, DEFAULT_LANG)

    def test_is_valid(self):

        self.assertTrue(localization.is_valid_langcode("en"))
        self.assertTrue(localization.is_valid_langcode("eo"))
        self.assertTrue(localization.is_valid_langcode("en_US"))
        self.assertTrue(localization.is_valid_langcode("csb"))
        self.assertTrue(localization.is_valid_langcode("cs_CZ.UTF-8@latin"))
        self.assertTrue(localization.is_valid_langcode("ca_ES.UTF-8@valencia"))

        self.assertTrue(localization.is_valid_langcode("cs_JA.iso8859-1@cyrl"))
        # nonsensical but still valid - parses correctly and has a language name

        self.assertFalse(localization.is_valid_langcode("blah"))
        self.assertFalse(localization.is_valid_langcode(""))
        self.assertFalse(localization.is_valid_langcode(None))

    def test_invalid_raise_decorator(self):
        self.assertRaises(localization.InvalidLocaleSpec, localization.get_native_name, "blah")
        self.assertRaises(localization.InvalidLocaleSpec, localization.is_supported_locale, "blah")

    def test_is_supported(self):
        self.assertTrue(localization.is_supported_locale("en"))
        self.assertTrue(localization.is_supported_locale("en_US"))
        self.assertTrue(localization.locale_supported_in_console("en"))
        self.assertTrue(localization.locale_supported_in_console("en_US"))

    def test_native_name(self):
        self.assertEqual(localization.get_native_name("de"), "Deutsch")
        self.assertEqual(localization.get_native_name("cs_CZ"), "Čeština (Česko)")

    def test_english_name(self):
        self.assertEqual(localization.get_english_name("de"), "German")
        self.assertEqual(localization.get_english_name("cs_CZ"), "Czech (Czechia)")

    def test_available_translations(self):
        self.assertIn("en", localization.get_available_translations())

    def test_territory_locales(self):
        self.assertIn("en_US.UTF-8", localization.get_territory_locales("US"))
        self.assertIn("en_GB.UTF-8", localization.get_territory_locales("GB"))

    def test_locale_keyboards(self):
        self.assertEqual(localization.get_locale_keyboards("en_US"), ["us"])
        self.assertEqual(localization.get_locale_keyboards("en_GB"), ["gb"])

    def test_common_keyboard_layouts(self):
        layouts = localization.get_common_keyboard_layouts()
        self.assertIn("us", layouts)
        self.assertIn("fr(oss)", layouts)
        self.assertIn("de(nodeadkeys)", layouts)

    def test_locale_timezones(self):
        self.assertIn("Europe/Oslo", localization.get_locale_timezones("no"))

    @patch.dict("pyanaconda.localization.os.environ", dict())
    def test_xlated_tz(self):
        localization.os.environ["LANG"] = "en_US"
        self.assertEqual("Europe/Barcelona", localization.get_xlated_timezone("Europe/Barcelona"))
        localization.os.environ["LANG"] = "cs_CZ"
        self.assertEqual("Evropa/Praha", localization.get_xlated_timezone("Europe/Prague"))
        localization.os.environ["LANG"] = "blah"
        self.assertRaises(localization.InvalidLocaleSpec,
                          localization.get_xlated_timezone,
                          "America/New_York")


class SetupLocaleTest(unittest.TestCase):

    def tearDown(self):
        locale_mod.setlocale(locale_mod.LC_ALL, DEFAULT_LANG)

    @patch("pyanaconda.localization.setenv")
    @patch("pyanaconda.localization.locale_mod.setlocale")
    @patch("pyanaconda.localization.set_modules_locale")
    def test_setup_locale_notext(self, set_modules_locale_mock, setlocale_mock, setenv_mock):
        """Test setup_locale in GUI mode"""

        loc_proxy = MagicMock()

        locale = localization.setup_locale("sk", localization_proxy=loc_proxy)

        loc_proxy.SetLanguage.assert_called_once_with("sk")
        setenv_mock.assert_called_once_with("LANG", "sk")
        setlocale_mock.assert_called_once_with(locale_mod.LC_ALL, "sk")
        set_modules_locale_mock.assert_called_once_with("sk")

        self.assertEqual(locale, "sk")

    @patch.dict("pyanaconda.localization.os.environ", dict())
    @patch("pyanaconda.localization.locale_supported_in_console", return_value=False)
    @patch("pyanaconda.localization.setenv")
    @patch("pyanaconda.localization.locale_mod.setlocale")
    @patch("pyanaconda.localization.set_modules_locale")
    def test_setup_locale_text(self, set_modules_locale_mock, setlocale_mock, setenv_mock,
                               locale_supported_in_console_mock):
        """Test setup_locale in TUI mode"""
        # note: to eliminate unpredictable support in console, mocking such that it always fails

        locale = localization.setup_locale("ja_JP", text_mode=True)

        locale_supported_in_console_mock.assert_called_once_with("ja_JP")
        self.assertEqual(localization.os.environ["LANG"], DEFAULT_LANG)
        setenv_mock.assert_called_once_with("LANG", DEFAULT_LANG)
        setlocale_mock.assert_called_once_with(locale_mod.LC_ALL, DEFAULT_LANG)
        set_modules_locale_mock.assert_called_once_with(DEFAULT_LANG)

        self.assertEqual(locale, DEFAULT_LANG)

    @patch("pyanaconda.localization.setenv")
    @patch("pyanaconda.localization.locale_mod.setlocale", side_effect=[locale_mod.Error, None])
    @patch("pyanaconda.localization.set_modules_locale")
    def test_setup_locale_setlocale_fail(self, set_modules_locale_mock, setlocale_mock, setenv_mock):
        """Test setup_locale with failure in setlocale"""

        locale = localization.setup_locale("es_ES")

        setenv_mock.assert_has_calls([
            call("LANG", "es_ES"),
            call("LANG", DEFAULT_LANG)
        ])
        setlocale_mock.assert_has_calls([
            call(locale_mod.LC_ALL, "es_ES"),
            call(locale_mod.LC_ALL, DEFAULT_LANG)
        ])
        setlocale_mock.assert_called_with(locale_mod.LC_ALL, DEFAULT_LANG)
        set_modules_locale_mock.assert_called_once_with(DEFAULT_LANG)

        self.assertEqual(locale, DEFAULT_LANG)


class SetupLocaleEnvironmentTest(unittest.TestCase):

    @patch("pyanaconda.localization.get_language_locales")
    @patch.dict("pyanaconda.localization.os.environ",
                {"LANGUAGE": "de", "LANG": "de", "LC_ALL": "de", "LC_MESSAGES": "de"})
    def test_setup_locale_environment_param_ok(self, locales_mock):
        """Test setup_locale_environment() with parameter"""
        # success case
        locales_mock.return_value = ["fr_FR.UTF-8"]

        localization.setup_locale_environment("fr")

        self.assertEqual("fr_FR.UTF-8", localization.os.environ["LANG"])
        self.assertNotIn("LANGUAGE", localization.os.environ)
        self.assertNotIn("LC_MESSAGES", localization.os.environ)
        self.assertNotIn("LC_ALL", localization.os.environ)

        # mock a failure
        locales_mock.return_value = []
        locales_mock.side_effect = localization.InvalidLocaleSpec

        localization.setup_locale_environment("iu")

        self.assertIn(DEFAULT_LANG, localization.os.environ["LANG"])

    @patch.dict("pyanaconda.localization.os.environ", dict())
    def test_setup_locale_environment_vars(self):
        """Test setup_locale_environment() with multiple environment variables"""
        for varname in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):

            localization.os.environ.clear()
            localization.os.environ[varname] = "ko"

            localization.setup_locale_environment(None)

            self.assertEqual("ko_KR.UTF-8", localization.os.environ["LANG"])
            if varname != "LANG":
                self.assertNotIn(varname, localization.os.environ)

    @patch.dict("pyanaconda.localization.os.environ", {"LANG": "blah"})
    def test_setup_locale_environment_vars_invalid(self):
        """Test setup_locale_environment() with invalid environment variable input"""
        localization.setup_locale_environment(None)

        self.assertEqual(DEFAULT_LANG, localization.os.environ["LANG"])

    @patch("pyanaconda.localization.open")
    @patch.dict("pyanaconda.localization.os.environ", dict())
    def test_setup_locale_environment_fallback_efi_ok(self, open_mock):
        """Test setup_locale_environment() fallback to EFI vars"""
        # success with valid data
        # first 4 bytes binary attributes, then language with - instead of _, minimum 10 bytes
        open_mock.return_value = StringIO("\x07\x00\x00\x00de-DE\x00")
        localization.os.environ.clear()

        localization.setup_locale_environment(None)

        self.assertTrue(open_mock.called)
        self.assertIn("de", localization.os.environ["LANG"])

    @patch("pyanaconda.localization.open")
    @patch.dict("pyanaconda.localization.os.environ", dict())
    def test_setup_locale_environment_fallback_efi_bad(self, open_mock):
        """Test setup_locale_environment() fallback to EFI vars with bad contents"""
        # failure with invalid data - too short
        open_mock.return_value = StringIO("\x00")

        localization.setup_locale_environment(None)

        self.assertEqual(DEFAULT_LANG, localization.os.environ["LANG"])


class LangcodeLocaleMatchingTests(unittest.TestCase):

    def tearDown(self):
        locale_mod.setlocale(locale_mod.LC_ALL, DEFAULT_LANG)

    def test_find_best_locale_match(self):
        """Finding best locale matches should work as expected."""
        # can find best matches
        self.assertEqual(localization.find_best_locale_match("cs_CZ", ["cs", "cs_CZ", "en", "en_US"]), "cs_CZ")
        self.assertEqual(localization.find_best_locale_match("cs", ["cs_CZ", "cs", "en", "en_US"]), "cs")
        self.assertEqual(localization.find_best_locale_match("pt_BR", ["pt", "pt_BR"]), "pt_BR")
        self.assertEqual(localization.find_best_locale_match("pt_BR", ["pt", "pt_BR", "pt_PT"]), "pt_BR")
        self.assertEqual(localization.find_best_locale_match("cs_CZ.UTF-8", ["cs", "cs_CZ", "cs_CZ.UTF-8"]),
                         "cs_CZ.UTF-8")
        self.assertEqual(localization.find_best_locale_match("cs_CZ.UTF-8@latin",
                                                             ["cs", "cs_CZ@latin", "cs_CZ.UTF-8"]), "cs_CZ@latin")

        # no matches
        self.assertIsNone(localization.find_best_locale_match("pt_BR", ["en_BR", "en"]))
        self.assertIsNone(localization.find_best_locale_match("cs_CZ.UTF-8", ["en", "en.UTF-8"]))

        # nonsense
        self.assertIsNone(localization.find_best_locale_match("ja", ["blah"]))
        self.assertIsNone(localization.find_best_locale_match("blah", ["en_US.UTF-8"]))

    # TODO: Remove this skip when environment is stable again.
    @unittest.skip("Getting: 'UnicodeDecodeError' on some environments.")
    def test_resolve_date_format(self):
        """All locales' date formats should be properly resolved."""
        locales = (line.strip() for line in execWithCapture("locale", ["-a"]).splitlines())
        for locale in locales:
            locale_mod.setlocale(locale_mod.LC_ALL, locale)
            order = localization.resolve_date_format(1, 2, 3, fail_safe=False)[0]
            for i in (1, 2, 3):
                self.assertIn(i, order)
