# Simple Addition Workflow

This workflow generates two random numbers and adds them together.

## BOX: generate_numbers
Generates two random integers between 1 and 100.
**Inputs:** seed
```python
import random

def execute(seed=None):
    if seed is not None:
        random.seed(0)
    num1 = random.randint(1, 100)
    num2 = random.randint(1, 100)
    print(f"Generated numbers: {num1}, {num2}")
    # Output must be a dictionary
    return {"number1": num1, "number2": num2}
```

## BOX: add_numbers
Adds the two numbers received as input.
**Inputs:** input_data
```python
def execute(input_data):
    # input_data is the dictionary from generate_numbers, e.g., {"number1": N1, "number2": N2}
    num1 = input_data.get('number1', 0) # Use .get for safety, default to 0 if key missing
    num2 = input_data.get('number2', 0)
    print(f"Adding {num1} + {num2}")
    total = num1 + num2
    # Output must be a dictionary
    return {"sum": total}
```

## CONNECTIONS
# Connect the outputs of generate_numbers to the inputs of add_numbers
generate_numbers.output -> add_numbers.input_data

## VISUAL_LAYOUT
# Optional layout hints for the visualizer
generate_numbers: {"x": 100, "y": 150}
add_numbers: {"x": 400, "y": 150}
