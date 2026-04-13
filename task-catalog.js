window.AGENTIC_TASK_CATALOG = {
  // Python
  "requests-header-injection": {
    "description": "Fix is_valid_header_value to reject LF characters, preventing HTTP header injection.",
    "category": "Python",
    "difficulty": "easy",
    "localPath": "repos/requests"
  },
  "werkzeug-cookie-maxage": {
    "description": "Clamp negative Max-Age cookie attribute values to 0 per RFC 6265.",
    "category": "Python",
    "difficulty": "easy",
    "localPath": "repos/werkzeug"
  },
  "click-intrange-open-bounds": {
    "description": "Fix open-bound (exclusive) comparison in IntRange validator so boundary value is correctly rejected.",
    "category": "Python",
    "difficulty": "medium",
    "localPath": "repos/click"
  },
  "flask-json-datetime": {
    "description": "Include time component when serialising datetime objects to JSON (not just the date).",
    "category": "Python",
    "difficulty": "medium",
    "localPath": "repos/flask"
  },
  "httpx-backoff-formula": {
    "description": "Fix exponential back-off to use base * 2**attempt (multiplication) not base + 2**attempt.",
    "category": "Python",
    "difficulty": "hard",
    "localPath": "repos/httpx"
  },
  // Go
  "viper-config-merge": {
    "description": "Deep-merge nested config maps recursively instead of overwriting the whole nested map.",
    "category": "Go",
    "difficulty": "easy",
    "localPath": "repos/viper"
  },
  "cobra-nil-map-panic": {
    "description": "Handle nil flag-set map safely in ValidateRequiredFlags without panicking.",
    "category": "Go",
    "difficulty": "easy",
    "localPath": "repos/cobra"
  },
  "gin-query-empty-param": {
    "description": "Return (0, false) for empty string in ParseIntQueryParam to distinguish absent from zero.",
    "category": "Go",
    "difficulty": "medium",
    "localPath": "repos/gin"
  },
  "validator-printable-ascii-tab": {
    "description": "Reject tab (0x09) in IsASCIIPrintable — printable ASCII is 0x20–0x7E only.",
    "category": "Go",
    "difficulty": "medium",
    "localPath": "repos/validator"
  },
  "testify-nil-vs-empty-slice": {
    "description": "Distinguish nil slice from empty slice in SlicesEqual (nil != []int{}).",
    "category": "Go",
    "difficulty": "hard",
    "localPath": "repos/testify"
  },
  // JavaScript
  "commander-split-description": {
    "description": "Trim whitespace from the main description in splitDescription, not just the hint.",
    "category": "JavaScript",
    "difficulty": "easy",
    "localPath": "repos/commander.js"
  },
  "lodash-round-negative-exp": {
    "description": "Fix round() for values with negative scientific-notation exponents (< 1).",
    "category": "JavaScript",
    "difficulty": "easy",
    "localPath": "repos/lodash"
  },
  "datefns-month-zero-pad": {
    "description": "Add +1 to getMonth() result so January renders as '01' not '00'.",
    "category": "JavaScript",
    "difficulty": "medium",
    "localPath": "repos/date-fns"
  },
  "axios-double-slash-url": {
    "description": "Strip leading slash from relativeURL in buildURL to prevent double slashes.",
    "category": "JavaScript",
    "difficulty": "medium",
    "localPath": "repos/axios"
  },
  "marked-escape-order": {
    "description": "Move & replacement first in escapeHTML to prevent double-escaping of entities.",
    "category": "JavaScript",
    "difficulty": "hard",
    "localPath": "repos/marked"
  },
  // TypeScript
  "zod-optional-validate": {
    "description": "Skip required-field check for optional fields in SchemaBuilder.validate().",
    "category": "TypeScript",
    "difficulty": "easy",
    "localPath": "repos/zod"
  },
  "class-transformer-nested-keys": {
    "description": "Support dot-notation nested key paths like 'address.city' in transform().",
    "category": "TypeScript",
    "difficulty": "medium",
    "localPath": "repos/class-transformer"
  },
  "ts-pattern-wildcard-order": {
    "description": "Check specific patterns before the wildcard '_' branch in match().",
    "category": "TypeScript",
    "difficulty": "medium",
    "localPath": "repos/ts-pattern"
  },
  "yup-collect-all-errors": {
    "description": "Remove early break in Validator so all failing rules are reported, not just the first.",
    "category": "TypeScript",
    "difficulty": "easy",
    "localPath": "repos/yup"
  },
  "typeorm-and-conditions": {
    "description": "Join multiple WHERE conditions with AND instead of OR in QueryBuilder.build().",
    "category": "TypeScript",
    "difficulty": "hard",
    "localPath": "repos/typeorm"
  },
  // React
  "react-hook-form-reset-baseline": {
    "description": "Update _initial in reset() so dirty checks use the new values as baseline.",
    "category": "React",
    "difficulty": "easy",
    "localPath": "repos/react-hook-form"
  },
  "zustand-persist-hydrate": {
    "description": "Merge persisted state with defaults in hydrate() so missing keys fall back to defaults.",
    "category": "React",
    "difficulty": "easy",
    "localPath": "repos/zustand"
  },
  "jotai-derived-recompute": {
    "description": "Invalidate derived-atom cache when a dependency atom changes via set().",
    "category": "React",
    "difficulty": "medium",
    "localPath": "repos/jotai"
  },
  "tanstack-query-staletime": {
    "description": "Fix isFresh() so staleTime=0 is always stale and the staleTime boundary is exclusive.",
    "category": "React",
    "difficulty": "medium",
    "localPath": "repos/tanstack-query"
  },
  "react-router-wildcard-match": {
    "description": "Fix * wildcard in matchPath() to consume remaining path segments instead of matching the literal '*'.",
    "category": "React",
    "difficulty": "hard",
    "localPath": "repos/react-router"
  },
};
