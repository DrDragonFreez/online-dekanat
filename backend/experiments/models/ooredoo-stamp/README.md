---

tags:
- object-detection
- yolos
- stamp-detection
- computer-vision
license: apache-2.0
language: en
model-index:
- name: ooredoo-stamp-detection
  results:
  - task:
      type: object-detection
      name: Object Detection
    metrics:
    - type: mAP
      value: 0.99
      name: mAP

---
# Ooredoo Stamp Detection Model

A fine-tuned YOLOS model for detecting stamps in documents.

## Model Description

This model is based on `hustvl/yolos-small` and fine-tuned for single-class stamp detection in documents. It can identify and localize stamps with high accuracy.

- **Base Model**: hustvl/yolos-small
- **Task**: Object Detection
- **Classes**: 1 (stamp)
- **Input**: RGB images
- **Output**: Bounding boxes + confidence scores

## Author

- **V. Hisamutdinovs**

## Usage

```python
from transformers import AutoImageProcessor, AutoModelForObjectDetection
from PIL import Image
import torch

# Load model
processor = AutoImageProcessor.from_pretrained("Ooredoo-Group/ooredoo-stamp-detection")
model = AutoModelForObjectDetection.from_pretrained("Ooredoo-Group/ooredoo-stamp-detection")

# Inference
image = Image.open("document_with_stamp.jpg")
inputs = processor(images=image, return_tensors="pt")
outputs = model(**inputs)

# Post-process results
target_sizes = torch.tensor([image.size[::-1]])
results = processor.post_process_object_detection(outputs, target_sizes=target_sizes)[0]

# Display results
for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
    print(f"Detected stamp with confidence {score:.2f}")
    print(f"Bounding box: {box}")
```

## Training Data

- **Total Images**: 350
- **Total Annotations**: 711 bounding boxes
- **Format**: COCO format
- **Split**: Train (80%) / Val (15%) / Test (5%)
- **Sources**: Kaggle stamp dataset + HuggingFace datasets

## Performance

- **Confidence**: High confidence detections (0.99+)
- **Accuracy**: Excellent performance on document stamp detection
- **Speed**: Fast inference suitable for production use

## Limitations

- Designed specifically for stamp detection
- Performance may vary on different document types
- Requires proper image preprocessing

## Organization

**Ooredoo-Group** 

## License

Apache-2.0