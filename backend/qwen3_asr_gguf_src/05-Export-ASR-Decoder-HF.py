import os
import sys
import json
import torch
from pathlib import Path
from safetensors.torch import save_file

# Add project root to sys.path to import qwen_asr
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from qwen_asr.core.transformers_backend.modeling_qwen3_asr import Qwen3ASRForConditionalGeneration
from transformers import AutoTokenizer

from export_config import ASR_MODEL_DIR, EXPORT_DIR

def extract_llm_weights():
    print(f"Loading Qwen3-ASR model from: {ASR_MODEL_DIR}")
    
    # Load the full ASR model
    # We use trust_remote_code=True because Qwen3ASR might rely on it, though we are importing class directly
    # Using the class directly ensures we use the local code we analyzed
    model = Qwen3ASRForConditionalGeneration.from_pretrained(ASR_MODEL_DIR, trust_remote_code=True, device_map="cpu")
    
    output_dir = Path(EXPORT_DIR) / "asr_decoder_hf"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Extracting LLM (Thinker) weights to: {output_dir}")
    
    # 1. Prepare Configuration
    # We extract the text config from the thinker config
    text_config = model.config.thinker_config.text_config
    
    # Convert to dictionary for modification
    llm_config_dict = text_config.to_dict()
    
    # Modify architectures and model_type for Qwen3-VL disguise/compatibility
    llm_config_dict["architectures"] = ["Qwen3VLForConditionalGeneration"]
    llm_config_dict["model_type"] = "qwen3_vl"
    
    # Ensure RoPE scaling is preserved (important for mrope)
    if not hasattr(text_config, "rope_scaling") or text_config.rope_scaling is None:
        # If original config didn't have explicit rope_scaling but used mrope defaults in code,
        # we might need to add it explicitly if the target runner expects it.
        # For now, we trust the config extracted from the model.
        pass
        
    # Save config
    with open(output_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump(llm_config_dict, f, indent=2, ensure_ascii=False)
    print("Saved config.json")
    
    # 2. Extract Weights
    # We need to map `thinker.model.*` to `model.*`
    # and `thinker.lm_head.*` to `lm_head.*`
    
    as_state_dict = model.state_dict()
    new_state_dict = {}
    
    keys_to_extract = []
    
    for key in as_state_dict.keys():
        if key.startswith("thinker.model."):
            new_key = key.replace("thinker.model.", "model.")
            new_state_dict[new_key] = as_state_dict[key]
            keys_to_extract.append(key)
        elif key.startswith("thinker.lm_head."):
            new_key = key.replace("thinker.lm_head.", "lm_head.")
            # Clone to separate memory from embed_tokens if they are tied
            new_state_dict[new_key] = as_state_dict[key].clone()
            keys_to_extract.append(key)
    
    print(f"Extracted {len(new_state_dict)} tensors.")
    
    # Save weights
    save_file(new_state_dict, output_dir / "model.safetensors")
    print("Saved model.safetensors")
    
    # 3. Save Tokenizer
    # We can load the tokenizer from the original directory and save it to the new one
    print("Saving tokenizer...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(ASR_MODEL_DIR, trust_remote_code=True)
        tokenizer.save_pretrained(output_dir)
        print("Saved tokenizer")
    except Exception as e:
        print(f"Warning: Failed to save tokenizer: {e}")
        
    print("\n✅ Extraction complete!")

if __name__ == "__main__":
    extract_llm_weights()
