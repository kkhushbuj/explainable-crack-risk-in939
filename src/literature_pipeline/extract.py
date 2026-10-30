import os
import re
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Optional, List
from langchain_community.document_loaders import PyPDFLoader
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
import pandas as pd

load_dotenv()

# ---- STEP 1: Per-sample record ----
class SampleRecord(BaseModel):
    sample_id: Optional[str] = Field(description="Sample name/number as given in the paper, e.g. 'Sample 8', 'S19'")
    laser_power_W: Optional[str] = Field(description="Laser power actually used to fabricate THIS specific sample. If the paper states power varies by zone/region within one build (e.g. contour vs core), report that range as-is.")
    scan_speed_mms: Optional[str] = Field(description="Scan speed actually used to fabricate THIS specific sample")
    layer_thickness_um: Optional[str] = Field(description="Layer thickness actually used for THIS specific sample")
    hatch_spacing_mm: Optional[str] = Field(description="Hatch spacing actually used for THIS specific sample")
    build_plate_temp_C: Optional[str] = Field(description="Preheat/build plate temperature for THIS specific sample, if it varies by sample")
    relative_density_percent: Optional[str] = Field(description="Relative density (%) measured for THIS sample")
    porosity_percent: Optional[str] = Field(description="Porosity (%) measured for THIS sample")
    crack_density: Optional[str] = Field(description="Crack density value measured for THIS sample")
    crack_occurred: Optional[str] = Field(description="Yes/No/Not clear for THIS specific sample")
    is_doped: Optional[str] = Field(description="Yes if this sample's material composition includes ANY additive/dopant beyond baseline IN939 (e.g. Si, Y2O3, TiC, TiB2, carbon, or any other element/particle addition). No if it is plain/baseline IN939. Not clear if composition isn't stated for this sample.")
    dopant_details: Optional[str] = Field(description="What was added and how much, e.g. '2 wt% Si', '1 wt% TiB2'. Leave null if is_doped is No or Not clear.")
    notes: Optional[str] = Field(description="Any other relevant detail about THIS specific sample")


class LPBFExtraction(BaseModel):
    material: Optional[str] = Field(description="Alloy/material(s) used, e.g. IN939")
    samples: List[SampleRecord] = Field(
        default_factory=list,
        description="""One entry per DISTINCT parameter combination/sample/experimental condition 
        ACTUALLY FABRICATED AND TESTED IN THIS PAPER'S OWN EXPERIMENTS. Each sample's laser_power_W, 
        scan_speed_mms, etc. must reflect what was ACTUALLY used for THAT sample, exactly as the paper 
        states it — including if the paper itself reports a range because the value legitimately 
        varied within that one build. DO NOT invent a range by combining values from DIFFERENT samples 
        together, and DO NOT copy a range from a background/literature-review section discussing OTHER 
        researchers' work. For EVERY sample, also determine is_doped and dopant_details based on that 
        sample's specific material composition."""
    )
    scan_strategy: Optional[str] = Field(description="Scan pattern used (paper-wide, if consistent)")
    scan_strategy_evidence: Optional[str] = Field(description="Exact quote. If not mentioned, say 'Not mentioned in text'")
    build_plate_temp_C: Optional[str] = Field(description="Build plate/preheat temperature(s) tested (paper-wide summary)")
    build_plate_temp_evidence: Optional[str] = Field(description="Exact quote. If not mentioned, say 'Not mentioned in text'")
    shielding_gas: Optional[str] = Field(description="Shielding gas used")
    shielding_gas_evidence: Optional[str] = Field(description="Exact quote. If not mentioned, say 'Not mentioned in text'")
    optimal_parameters: Optional[str] = Field(description="Paper's stated BEST/optimal parameter combination, if identified")
    optimal_parameters_evidence: Optional[str] = Field(description="Exact quote. If not mentioned, say 'Not mentioned in text'")
    crack_type: Optional[str] = Field(description="Type(s) of crack reported")
    crack_type_evidence: Optional[str] = Field(description="Exact quote. If not mentioned, say 'Not mentioned in text'")
    crack_location: Optional[str] = Field(description="Where cracks appeared")
    crack_location_evidence: Optional[str] = Field(description="Exact quote. If not mentioned, say 'Not mentioned in text'")
    crack_cause: Optional[str] = Field(description="Reported cause/mechanism of cracking")
    crack_cause_evidence: Optional[str] = Field(description="Exact quote. If not mentioned, say 'Not mentioned in text'")
    sensor_methods_used: Optional[str] = Field(description="Any monitoring/characterization methods used")
    sensor_methods_evidence: Optional[str] = Field(description="Exact quote. If not mentioned, say 'Not mentioned in text'")
    mechanical_test_results: Optional[str] = Field(description="Tensile/hardness/fatigue results reported")
    mechanical_test_evidence: Optional[str] = Field(description="Exact quote. If not mentioned, say 'Not mentioned in text'")
    source_paper_summary: Optional[str] = Field(description="One-sentence summary of what this paper studied")


llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0)
structured_llm = llm.with_structured_output(LPBFExtraction)

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a materials science research assistant extracting data from a paper about 
metal additive manufacturing (LPBF - Laser Powder Bed Fusion).

CRITICAL INSTRUCTION ON SAMPLES:
Extract EACH DISTINCT experimental condition THIS PAPER ITSELF fabricated and tested as a SEPARATE 
entry in the 'samples' list.

IMPORTANT DISTINCTION:
1. This paper's OWN experimental data — extract this.
2. Background/literature review text citing OTHER researchers' work — do NOT extract this as this 
   paper's own sample data.

Note: it is NORMAL and CORRECT for a single build/sample to legitimately use a laser power or scan 
speed RANGE if the paper explicitly states settings varied by print zone within that one build. 
Report the range exactly as stated in that case - this is real data, not an error.

CRITICAL INSTRUCTION ON MATERIAL DOPING/COMPOSITION:
For EVERY sample, check what material composition applies to THAT specific sample. Set is_doped = 
"Yes" if that specific sample includes ANY additive beyond baseline IN939. Set is_doped = "No" if 
it is plain baseline IN939. Record the exact additive and amount in dopant_details.

GENERAL RULES:
1. For paper-level fields, provide the EXACT sentence/quote as evidence.
2. If a field is not mentioned anywhere in the text, set the value to null and evidence to 'Not mentioned in text'.
3. Do not guess or infer values that are not explicitly stated.
4. Only extract what is actually written in the given text."""),
    ("human", "Here is the paper text:\n\n{paper_text}")
])

extraction_chain = prompt | structured_llm


def extract_from_pdf(pdf_path):
    loader = PyPDFLoader(pdf_path)
    pages = loader.load()
    full_text = "\n".join([page.page_content for page in pages])
    if not full_text.strip():
        raise ValueError("No extractable text found in this PDF")
    max_chars = 100000
    if len(full_text) > max_chars:
        full_text = full_text[:max_chars]
    return extraction_chain.invoke({"paper_text": full_text})


def parse_numbers(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return []
    return [float(n) for n in re.findall(r'\d+\.?\d*', str(val))]

def is_wide_range(val, max_span):
    nums = parse_numbers(val)
    return len(nums) >= 2 and (max(nums) - min(nums)) > max_span

FLAG_SPANS = {
    "laser_power_W": 100,
    "scan_speed_mms": 1500,
    "hatch_spacing_mm": 0.1,
    "layer_thickness_um": 50,
}

def flag_sample(sample_dict):
    flags = [f for f, span in FLAG_SPANS.items() if is_wide_range(sample_dict.get(f), span)]
    sample_dict["flagged_for_review"] = ", ".join(flags) if flags else None
    return sample_dict


def flatten_to_rows(extraction_result, source_file):
    paper_level = extraction_result.model_dump()
    samples = paper_level.pop("samples")
    rows = []
    if not samples:
        row = {**paper_level, "sample_id": None, "flagged_for_review": None, "source_file": source_file}
        rows.append(row)
    else:
        for sample in samples:
            sample = flag_sample(sample)
            row = {**paper_level, **sample, "source_file": source_file}
            rows.append(row)
    return rows


def process_new_papers_only(folder_path, output_csv):
    """Only processes PDFs NOT already present in output_csv's source_file column.
    Appends new results to the existing CSV instead of overwriting everything."""

    if not os.path.isdir(folder_path):
        print(f"ERROR: Folder not found: {folder_path}")
        return pd.DataFrame()

    all_pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]

    # Load existing CSV (if it exists) to see which papers are already done
    if os.path.exists(output_csv):
        existing_df = pd.read_csv(output_csv)
        already_done = set(existing_df["source_file"].unique())
        print(f"Existing CSV found: {len(existing_df)} rows from {len(already_done)} paper(s)")
    else:
        existing_df = pd.DataFrame()
        already_done = set()
        print("No existing CSV found - will create a new one.")

    new_pdf_files = [f for f in all_pdf_files if f not in already_done]

    print(f"Total PDFs in folder: {len(all_pdf_files)}")
    print(f"Already processed (skipping): {len(all_pdf_files) - len(new_pdf_files)}")
    print(f"NEW papers to process: {len(new_pdf_files)}\n")

    if not new_pdf_files:
        print("Nothing new to process. All papers already in the CSV.")
        return existing_df

    new_rows = []
    for i, filename in enumerate(new_pdf_files, 1):
        pdf_path = os.path.join(folder_path, filename)
        print(f"[{i}/{len(new_pdf_files)}] Processing NEW paper: {filename}")
        try:
            result = extract_from_pdf(pdf_path)
            rows = flatten_to_rows(result, filename)
            new_rows.extend(rows)
            flagged_count = sum(1 for r in rows if r.get("flagged_for_review"))
            doped_count = sum(1 for r in rows if str(r.get("is_doped")).lower() == "yes")
            note = []
            if flagged_count: note.append(f"{flagged_count} flagged")
            if doped_count: note.append(f"{doped_count} doped")
            note_str = f" ({', '.join(note)})" if note else ""
            print(f"    -> {len(rows)} row(s) extracted (material: {result.material}){note_str}")
        except Exception as e:
            print(f"    FAILED: {e}")
            new_rows.append({"source_file": filename, "error": str(e)})

    new_df = pd.DataFrame(new_rows)
    combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    combined_df.to_csv(output_csv, index=False)

    print(f"\n{'='*60}")
    print(f"Added {len(new_df)} new row(s) from {len(new_pdf_files)} new paper(s)")
    print(f"Total dataset now: {len(combined_df)} rows from {combined_df['source_file'].nunique()} papers")
    print(f"Saved to: {output_csv}")
    print(f"{'='*60}")
    return combined_df


if __name__ == "__main__":
    input_folder = "data/raw_paper/high_value"
    output_csv = "data/literature_extracted/high_value_data.csv"

    df = process_new_papers_only(input_folder, output_csv)