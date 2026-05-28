# PROJ-05 Gemini CLI Architecture Review — 2026-05-26 12:10 PDT
# Model: flash-fast | Cost: 1 flash query

## 3 Actionable Recommendations:

### 1. Refactor Aspect Calculations for True Vedic Graha Drishti
**Current:** Degree-difference logic for "special aspects"
**Issue:** Simplified interpretation. Vedic relies on whole-sign aspects, not just degree proximity. Mars in Aries aspects Leo (5th), Libra (7th), Scorpio (8th) regardless of exact degrees.
**Recommendation:** First determine aspected sign/house position per Vedic rules, THEN use degree orb for strength/gauge. This fundamental shift ensures engine aligns with core Vedic principles.

### 2. Implement Comprehensive Layered Validation with Schema-Based Checks
**Current:** Basic input validation at Chart.__init__
**Issue:** No validation for complex data structures or ephemeris data
**Recommendation:** Use Pydantic for data models. Validate data passed between calculation modules. Ensure planetary longitude stays within 0-360 after creation/modification.

### 3. Enhance Error Handling with Custom Exceptions and Structured Logging
**Current:** Generic `except Exception` blocks
**Issue:** No differentiation between ephemeris failures, math errors, config problems
**Recommendation:** Create exception hierarchy (`AstrologyError` → `EphemerisError`, `ChartInputError`, `CalculationError`). Add Python logging throughout for debugging and monitoring.
