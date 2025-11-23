"""Test script to debug Google search issues"""
import time
from googlesearch import search

print("Testing Google search...")
print("=" * 60)

try:
    query = "construction company Atlanta"
    print(f"Query: {query}")
    print("Attempting to search...")

    results = []
    for i, url in enumerate(search(query, num_results=5, lang='en', safe='off'), 1):
        print(f"{i}. {url}")
        results.append(url)
        time.sleep(2)

        if i >= 5:
            break

    print("=" * 60)
    print(f"Total results found: {len(results)}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
