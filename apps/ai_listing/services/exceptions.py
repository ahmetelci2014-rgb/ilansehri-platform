class AIListingError(Exception):
    code = "ai_listing_error"


class FeatureDisabledError(AIListingError):
    code = "feature_disabled"


class UsageLimitError(AIListingError):
    code = "usage_limit"


class DuplicateRequestError(AIListingError):
    code = "duplicate_request"


class ImageValidationError(AIListingError):
    code = "invalid_image"


class ProviderError(AIListingError):
    code = "provider_error"


class SchemaValidationError(AIListingError):
    code = "invalid_provider_output"


class SafetyBlockedError(AIListingError):
    code = "safety_blocked"
