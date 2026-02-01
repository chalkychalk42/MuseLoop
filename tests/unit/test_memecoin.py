"""Tests for memecoin content generator."""

from __future__ import annotations

from pathlib import Path

import pytest

from museloop.memecoin.generator import (
    ASSET_SPECS,
    TokenMeta,
    build_prompt,
    generate_brief,
    write_brief,
)


class TestTokenMeta:
    def test_basic_creation(self):
        token = TokenMeta(name="DogWifHat", ticker="WIF")
        assert token.name == "DogWifHat"
        assert token.ticker == "WIF"
        assert token.chain == "SOL"  # default
        assert token.vibe == "degen"  # default

    def test_full_creation(self):
        token = TokenMeta(
            name="PepeCoin",
            ticker="PEPE",
            concept="The OG meme frog",
            vibe="retro",
            colors=["#00ff00", "#000000"],
            tagline="Feel the green",
            chain="ETH",
        )
        assert token.concept == "The OG meme frog"
        assert token.chain == "ETH"
        assert len(token.colors) == 2

    def test_defaults(self):
        token = TokenMeta(name="Test", ticker="TST")
        assert len(token.colors) == 3
        assert token.website == ""
        assert token.twitter == ""


class TestBuildPrompt:
    def test_substitutes_all_fields(self):
        token = TokenMeta(
            name="MoonCat",
            ticker="MCAT",
            concept="Cats going to the moon",
            vibe="cute",
            colors=["#ff00ff"],
            tagline="To the moon!",
            chain="SOL",
        )
        template = "Token ${name} (${ticker}) — ${concept}, ${vibe} style, ${colors}. ${tagline}"
        result = build_prompt(template, token)
        assert "MoonCat" in result
        assert "MCAT" in result
        assert "Cats going to the moon" in result
        assert "cute" in result
        assert "#ff00ff" in result
        assert "To the moon!" in result

    def test_empty_concept_uses_default(self):
        token = TokenMeta(name="Test", ticker="TST", vibe="neon")
        result = build_prompt("${concept}", token)
        assert "neon memecoin" in result


class TestAssetSpecs:
    def test_all_specs_have_required_fields(self):
        for name, spec in ASSET_SPECS.items():
            assert "skill" in spec, f"{name} missing skill"
            assert "preset" in spec, f"{name} missing preset"
            assert "prompt_template" in spec, f"{name} missing prompt_template"
            assert "params" in spec, f"{name} missing params"

    def test_expected_assets_exist(self):
        expected = [
            "token_logo",
            "dexscreener_banner",
            "pumpfun_banner",
            "twitter_header",
            "twitter_profile",
            "twitter_post_announcement",
            "twitter_post_meme",
            "telegram_sticker",
            "discord_banner",
            "promo_video_thumbnail",
        ]
        for name in expected:
            assert name in ASSET_SPECS, f"Missing asset: {name}"

    def test_at_least_10_assets(self):
        assert len(ASSET_SPECS) >= 10


class TestGenerateBrief:
    def test_full_brief(self):
        token = TokenMeta(name="TestCoin", ticker="TST", concept="Testing")
        brief = generate_brief(token)
        assert "TestCoin" in brief["task"]
        assert "$TST" in brief["task"]
        assert brief["style"] == "degen"
        assert "plan_override" in brief
        assert len(brief["plan_override"]) == len(ASSET_SPECS)

    def test_filtered_assets(self):
        token = TokenMeta(name="Test", ticker="TST")
        brief = generate_brief(token, assets=["token_logo", "dexscreener_banner"])
        assert len(brief["plan_override"]) == 2

    def test_brief_has_skills(self):
        token = TokenMeta(name="Test", ticker="TST")
        brief = generate_brief(token)
        assert "flux_gen" in brief["skills_required"]

    def test_brief_has_constraints(self):
        token = TokenMeta(name="Test", ticker="TST", chain="ETH")
        brief = generate_brief(token)
        assert brief["constraints"]["chain"] == "ETH"
        assert brief["constraints"]["ticker"] == "TST"


class TestWriteBrief:
    def test_writes_json_file(self, tmp_path):
        token = TokenMeta(name="Test", ticker="TST")
        path = write_brief(token, str(tmp_path))
        assert path.exists()
        assert path.suffix == ".json"
        assert "tst" in path.name

    def test_file_is_valid_json(self, tmp_path):
        import json

        token = TokenMeta(name="Test", ticker="TST")
        path = write_brief(token, str(tmp_path))
        data = json.loads(path.read_text())
        assert "task" in data
        assert "plan_override" in data


class TestCryptoPresets:
    """Test that crypto export presets exist and are valid."""

    def test_dexscreener_banner(self):
        from museloop.export.presets import get_preset

        p = get_preset("dexscreener_banner")
        assert p.width == 1500
        assert p.height == 500

    def test_dexscreener_icon(self):
        from museloop.export.presets import get_preset

        p = get_preset("dexscreener_icon")
        assert p.width == 256
        assert p.height == 256

    def test_pumpfun_banner(self):
        from museloop.export.presets import get_preset

        p = get_preset("pumpfun_banner")
        assert p.width == 800
        assert p.height == 200

    def test_twitter_header(self):
        from museloop.export.presets import get_preset

        p = get_preset("twitter_header")
        assert p.width == 1500
        assert p.height == 500

    def test_twitter_profile(self):
        from museloop.export.presets import get_preset

        p = get_preset("twitter_profile")
        assert p.width == 400
        assert p.height == 400

    def test_telegram_sticker(self):
        from museloop.export.presets import get_preset

        p = get_preset("telegram_sticker")
        assert p.width == 512
        assert p.height == 512

    def test_token_logo_sizes(self):
        from museloop.export.presets import get_preset

        sm = get_preset("token_logo_sm")
        lg = get_preset("token_logo_lg")
        assert sm.width == 128
        assert lg.width == 1024

    def test_total_preset_count(self):
        from museloop.export.presets import PRESETS

        # 6 original + 11 crypto = 17
        assert len(PRESETS) >= 17
