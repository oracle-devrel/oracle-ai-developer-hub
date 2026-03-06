
from src.agents.self_reflection import SelfReflectionAgent
from termcolor import colored

def test_reflexion():
    print(colored("=== Testing SelfReflectionAgent ===", "green", attrs=["bold"]))
    agent = SelfReflectionAgent()
    
    # A tricky question that might induce hallucinations or incomplete answers initially
    query = "What is the capital of the country that has the city Timbuktu?"
    # Timbuktu is in Mali. Captial is Bamako.
    
    result = agent.run(query)
    # We print result inside the agent run, but here is the return value check
    print("\n[Done]")

if __name__ == "__main__":
    test_reflexion()
