# -*- coding: utf-8 -*-
import os
from core.qt_compat import cmds


class SearchService:
    def __init__(self, config_service):
        self.config_service = config_service

    @property
    def config(self):
        return self.config_service.config

    def search_tools(self, search_text):
        if not search_text or not search_text.strip():
            return []

        search_lower = search_text.strip().lower()
        results = []
        for tool in self.config.get("tools", []):
            tool_name = tool["name"].lower()
            if search_lower in tool_name:
                results.append(tool)
        return results

    def get_group_name_by_id(self, group_id):
        return self.config_service.get_group_name_by_id(group_id)

    def toggle_pin(self, tool):
        current = self.config_service.is_tool_pinned(tool)
        changed = self.config_service.set_tool_pinned(tool, not current)
        return changed
