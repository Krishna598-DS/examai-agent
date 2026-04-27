# test_async.py
import asyncio
import time

# "async def" means this function is a coroutine.
# A coroutine is a function that can PAUSE and let other code run,
# then RESUME from where it paused.
async def search_web(query):
    print(f"  [Search] Starting: {query}")
    
    # "await" means: start this operation, then PAUSE this coroutine
    # and let the event loop run something else while we wait.
    # asyncio.sleep() is the async version of time.sleep()
    # time.sleep() BLOCKS everything. asyncio.sleep() just pauses THIS coroutine.
    await asyncio.sleep(2)  # Simulates 2 second API call
    
    print(f"  [Search] Done: {query}")
    return f"Search results for: {query}"

async def read_pdf(filename):
    print(f"  [PDF] Starting: {filename}")
    await asyncio.sleep(3)  # Simulates 3 second PDF read
    print(f"  [PDF] Done: {filename}")
    return f"PDF content from: {filename}"

# --- Run them SEQUENTIALLY (still async but one at a time) ---
async def run_sequential():
    print("\n--- Sequential async ---")
    start = time.time()
    
    search_result = await search_web("JEE Newton's laws")
    pdf_result = await read_pdf("ncert_physics.pdf")
    
    print(f"Time taken: {time.time() - start:.1f}s")
    return search_result, pdf_result

# --- Run them CONCURRENTLY (the real power of async) ---
async def run_concurrent():
    print("\n--- Concurrent async ---")
    start = time.time()
    
    # asyncio.gather() runs ALL coroutines at the same time.
    # It starts search_web, immediately starts read_pdf without waiting,
    # then waits for BOTH to finish.
    # This is exactly what our orchestrator will do with multiple agents.
    search_result, pdf_result = await asyncio.gather(
        search_web("JEE Newton's laws"),
        read_pdf("ncert_physics.pdf")
    )
    
    print(f"Time taken: {time.time() - start:.1f}s")
    return search_result, pdf_result

# asyncio.run() creates the event loop and runs your async code.
# You can only call this from normal (non-async) code.
# Think of it as "start the engine."
asyncio.run(run_sequential())
asyncio.run(run_concurrent())
