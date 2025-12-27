from typing import List, Any

class Executor:

    def run_steps(self, steps: List[Any]) -> List[Any]:
        results = []
        for step in steps:
            if hasattr(step, 'execute'):
                results.append(step.execute())
            else:
                results.append(step())
        return results
