# wait_for2

## 0.3.1
- Added 3.10 compatibility

## 0.3.0
- Redesigned all wait-for handling branches to behave consistently
- Improved test coverage to 100% (with branch coverage)
- **Breaking change:** the `race_handler` callback is now passed a 2nd argument. It's a boolean indicating if the result was a raised exception.

## 0.2.0
- Added a callback-based handling option
- Made a simpler test to assert the different behaviours

## 0.1.0
- Initial release
