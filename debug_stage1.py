import asyncio
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Add base path for imports
_BASE_PATH = Path(__file__).parent
if str(_BASE_PATH) not in sys.path:
    sys.path.insert(0, str(_BASE_PATH))

# Load .env
load_dotenv(_BASE_PATH / ".env")

from stage1.stage_1 import run_stage_1
from stage1.stage1_models import Stage1Input

async def main():
    url = "https://www.percent.cn"
    print(f"Running Stage 1 for {url}...")
    
    input_data = Stage1Input(
        company_url=url,
        company_name="baifendian",
        industry="SaaS",
        language="en",
        region="us"
    )
    
    try:
        output = await run_stage_1(input_data)
        print("\n=== STAGE 1 OUTPUT ===")
        print(json.dumps(output.model_dump(), indent=2, default=str))
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
