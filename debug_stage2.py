import asyncio
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

_BASE_PATH = Path(__file__).parent
if str(_BASE_PATH) not in sys.path:
    sys.path.insert(0, str(_BASE_PATH))

load_dotenv(_BASE_PATH / ".env")

from stage1.stage1_models import CompanyContext
from stage2.stage_2 import run_stage_2
from stage2.stage2_models import Stage2Input


async def main():
    url = "https://www.percent.cn"
    print(f"Running Stage 2 only for {url} (mocked input)...")

    try:
        company_context = CompanyContext(
            company_name="Beijing Percent Information Technology Co., Ltd.",
            company_url=url,
            industry="Data Intelligence & AI",
            services=["Data Governance Consulting",
                "AI Model Development",
                "Intelligent Decision-Making Solutions",
                "Digital Transformation Consulting",
                "Customized Software Development",
                "Data Asset Management",
                "Public Opinion Monitoring"],
        )

        stage2_input = Stage2Input(
            company_context=company_context,
            language="en",
            region="us",
            target_count=20,
            enable_research=True,
        )

        stage2_output = await run_stage_2(stage2_input)
        print("\n=== STAGE 2 OUTPUT (mocked Stage2Input) ===")
        print(json.dumps(stage2_output.model_dump(), indent=2, default=str))

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
