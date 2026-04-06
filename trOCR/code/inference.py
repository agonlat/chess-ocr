import torch
from PIL import Image
import io
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

def model_fn(model_dir):
    processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
    model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")
    return model, processor

def predict_fn(data,model_and_processor):
    model,processor = model_and_processor
    image = Image.open(io.BytesIO(data)).convert("RGB")
    pixel_values = processor(images = image,return_tensors="pt").pixel_values

    generated_ids = model.generate(pixel_values)
    generated_text = processor.batch_decode(generated_ids,skip_special_tokens=True)

    return generated_text