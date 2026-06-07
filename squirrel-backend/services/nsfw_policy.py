from typing import Literal

EffectiveNsfwFilter = Literal["all", "yes", "no", "blocked"]


class NsfwPolicy:

    @staticmethod
    def resolve_effective_nsfw_filter(nsfw: str, show_nsfw: bool) -> EffectiveNsfwFilter:
        if not show_nsfw:
            if nsfw == "yes":
                return "blocked"
            return "no"

        if nsfw == "yes":
            return "yes"
        if nsfw == "no":
            return "no"
        return "all"


_default = NsfwPolicy()
resolve_effective_nsfw_filter = _default.resolve_effective_nsfw_filter
