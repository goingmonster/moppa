from datetime import datetime, timezone

from app.db.models import EventFilterRuleEntity
from app.models.s1_ingest_model import S1EventInputModel


class S1FilterService:
    def evaluate(
        self,
        event: S1EventInputModel,
        rules: list[EventFilterRuleEntity],
    ) -> tuple[str, list[str], int]:
        if not rules:
            return "passed", ["PASS_NO_ACTIVE_RULE"], 0

        applied = 0
        for rule in rules:
            applied += 1
            expression = rule.filter_expression.strip().lower()
            if expression == "keyword_include":
                matched, reason = self._keyword_include(event, rule.filter_config)
            elif expression == "keyword_exclude":
                matched, reason = self._keyword_exclude(event, rule.filter_config)
            elif expression == "credibility_min":
                matched, reason = self._credibility_min(event, rule.filter_config)
            elif expression == "event_time_within_hours":
                matched, reason = self._event_time_within_hours(event, rule.filter_config)
            elif expression == "content_length_min":
                matched, reason = self._content_length_min(event, rule.filter_config)
            else:
                matched, reason = True, "PASS_UNKNOWN_RULE_SKIPPED"

            if not matched:
                return "filtered", [reason], applied

        return "passed", ["PASS_RULES_CHECKED"], applied

    def _keyword_include(self, event: S1EventInputModel, config: dict[str, object]) -> tuple[bool, str]:
        keywords = self._get_keywords(config)
        mode = str(config.get("mode", "any")).lower()
        if not keywords:
            return True, "PASS_RULE_CONFIG_EMPTY"
        content = event.content.lower()
        if mode == "all":
            matched = all(keyword in content for keyword in keywords)
        else:
            matched = any(keyword in content for keyword in keywords)
        return (matched, "PASS_KEYWORD_INCLUDE") if matched else (False, "FILTER_KEYWORD_INCLUDE_NOT_MATCH")

    def _keyword_exclude(self, event: S1EventInputModel, config: dict[str, object]) -> tuple[bool, str]:
        keywords = self._get_keywords(config)
        if not keywords:
            return True, "PASS_RULE_CONFIG_EMPTY"
        content = event.content.lower()
        excluded = any(keyword in content for keyword in keywords)
        return (False, "FILTER_KEYWORD_EXCLUDE_MATCHED") if excluded else (True, "PASS_KEYWORD_EXCLUDE")

    def _credibility_min(self, event: S1EventInputModel, config: dict[str, object]) -> tuple[bool, str]:
        minimum = self._get_int(config.get("min"), 1)
        return (True, "PASS_CREDIBILITY_MIN") if event.credibility_level >= minimum else (False, "FILTER_LOW_CREDIBILITY")

    def _event_time_within_hours(self, event: S1EventInputModel, config: dict[str, object]) -> tuple[bool, str]:
        hours = self._get_int(config.get("hours"), 24)
        now = datetime.now(timezone.utc)
        delta_hours = (now - event.event_time).total_seconds() / 3600
        return (True, "PASS_TIME_WINDOW") if delta_hours <= hours else (False, "FILTER_OUTDATED_EVENT")

    def _content_length_min(self, event: S1EventInputModel, config: dict[str, object]) -> tuple[bool, str]:
        minimum = self._get_int(config.get("min"), 1)
        return (True, "PASS_CONTENT_LENGTH") if len(event.content.strip()) >= minimum else (False, "FILTER_CONTENT_TOO_SHORT")

    def _get_keywords(self, config: dict[str, object]) -> list[str]:
        raw = config.get("keywords")
        if not isinstance(raw, list):
            return []
        return [str(item).lower() for item in raw if str(item).strip()]

    def _get_int(self, value: object, default: int) -> int:
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return default
        return default
