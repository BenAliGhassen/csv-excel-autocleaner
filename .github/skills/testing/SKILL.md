---
name: testing
description: "Plan, write, review, and debug reliable automated tests. Use the project's existing test framework; for Python projects, apply pytest patterns for unit, integration, and end-to-end coverage."
---

# Testing

Use this skill when writing or improving tests, reviewing test quality, debugging flaky tests, or deciding what test coverage a change needs.

## Workflow

1. **Inspect before testing.** Read the code and existing tests around the behavior. Check the dependency manifests, test files, and configuration to identify the framework, conventions, and available tools. Do not add a second framework or change configuration without a need.
2. **Define the contract.** Identify observable inputs, outputs, state changes, side effects, errors, and important edge cases. Prioritize regressions that would affect users or callers.
3. **Choose the test level.** Use unit tests for isolated logic, integration tests for interactions between owned components, and a small number of end-to-end tests for critical user journeys. Prefer the lowest level that gives meaningful confidence.
4. **Design clear, independent tests.** Give each test a descriptive behavior-focused name and one main outcome. Use Arrange–Act–Assert structure. Set up its own state so test order and parallel execution do not affect results.
5. **Cover meaningful cases.** Include normal behavior, boundaries, invalid or missing input, and relevant failure paths. Use parameterization for related input/output cases instead of hiding cases in loops; give non-obvious cases readable IDs.
6. **Run and inspect.** Run the focused tests first, then the broadest relevant suite. Report the exact commands and observed results. Investigate failures rather than weakening assertions or silently skipping them.
7. **Review test value.** Confirm each test would fail if its behavior regressed, assertions check concrete outcomes, and mocks do not replace the behavior being tested. Report remaining gaps honestly.

## Python and pytest practices

- Use pytest functions, fixtures, and built-in fixtures rather than `unittest` setup methods. Keep fixtures focused and default to function scope; widen scope only for expensive resources that are safe to share.
- Put shared fixtures in the nearest appropriate `conftest.py`. Use yield fixtures for resources that need teardown, and ensure cleanup still runs on failures.
- Use `pytest.mark.parametrize` to express distinct cases as distinct reported test instances.
- Use `tmp_path` or `tmp_path_factory` for filesystem tests. Do not write test artifacts into the repository or rely on fixed temporary paths.
- Patch dependencies at the name and module where the code under test looks them up. Prefer `monkeypatch` or an already-installed pytest mocking plugin; do not install a plugin unless it is needed and approved by the project workflow.
- Avoid real network services, uncontrolled clocks, unseeded randomness, fixed ports, and shared mutable state in unit tests. Replace external boundaries deterministically; use a separate integration or end-to-end tier when real service behavior must be checked.
- Use `pytest.raises(..., match=...)` when the exception message is part of the contract, `pytest.warns` for expected warnings, and `pytest.approx` for floating-point comparisons.
- Declare and document custom markers in the project's existing pytest configuration. Enable strict marker checking if it fits the current setup; do not move configuration files just to follow a preferred convention.

## UI and end-to-end testing

- Exercise real user-observable behavior and assert specific visible results or state changes.
- Prefer accessible role, label, and text locators; use stable test IDs when needed. Avoid generated CSS classes, deep selectors, and positional selectors.
- Use framework auto-waiting and retrying assertions instead of fixed sleeps.
- Keep page or screen helpers small: centralize repeated navigation and selectors, while keeping expected outcomes in the test.
- Make end-to-end coverage selective and focused on important user flows; retain fast unit tests for detailed logic.

## Coverage and CI

- Treat coverage as a diagnostic and guardrail, not a substitute for strong assertions or a goal to test trivial lines.
- Measure coverage with the project's existing tool and options. Focus additional tests on meaningful uncovered branches and risk areas; do not weaken thresholds or add low-value tests to satisfy a number.
- Run tests in CI using the existing workflow. Keep expensive browser or external-service tests in an appropriate separate job or schedule when necessary.
- Add failure artifacts such as traces or screenshots only when the project's test stack supports them and they materially help diagnosis.

## Avoid

- Tests with no meaningful assertions, or tests that only confirm mocked behavior.
- One oversized test covering unrelated behaviors.
- Snapshotting large or volatile output without a clear review value.
- Assertions primarily coupled to private implementation details, incidental logs, or call counts when observable behavior is the actual contract.
- Broad exception handling that can hide test failures.
- Fixed sleeps, order-dependent tests, shared mutable fixtures, hard-coded paths or ports, and network access in unit tests.
- Quarantining or skipping a flaky test without documenting the reason and follow-up; treat quarantine as tracked debt.
- Changing application behavior solely to make an implementation-coupled test pass.
