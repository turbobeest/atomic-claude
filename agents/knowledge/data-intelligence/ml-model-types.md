# Machine Learning Model Types Quick Reference

> **Sources**:
> - https://scikit-learn.org/
> - https://pytorch.org/docs/
> - https://huggingface.co/docs/transformers/
> **Extracted**: 2025-12-21
> **Refresh**: Annually

## Model Categories

### Supervised Learning
**Input**: Labeled data (X, y pairs)
**Goal**: Learn mapping from inputs to outputs

| Task | Model Types | Use Cases |
|------|-------------|-----------|
| Classification | Logistic Regression, SVM, Random Forest, Neural Networks | Spam detection, image classification |
| Regression | Linear Regression, Gradient Boosting, Neural Networks | Price prediction, demand forecasting |

### Unsupervised Learning
**Input**: Unlabeled data (X only)
**Goal**: Discover patterns in data

| Task | Model Types | Use Cases |
|------|-------------|-----------|
| Clustering | K-Means, DBSCAN, Hierarchical | Customer segmentation, anomaly detection |
| Dimensionality Reduction | PCA, t-SNE, UMAP | Visualization, feature reduction |

### Semi-Supervised Learning
**Input**: Small amount of labeled + large amount of unlabeled
**Goal**: Leverage unlabeled data to improve performance

### Reinforcement Learning
**Input**: Environment, rewards
**Goal**: Learn optimal policy through trial and error

## Deep Learning Architectures

### Feedforward Networks (MLP)
- Fully connected layers
- Good for tabular data
- Simple classification/regression

### Convolutional Neural Networks (CNN)
- Spatial feature extraction
- Image classification, object detection
- Architecture: Conv → Pool → Conv → Pool → FC

### Recurrent Neural Networks (RNN/LSTM/GRU)
- Sequential data processing
- Time series, older NLP
- Largely superseded by Transformers for NLP

### Transformers
- Self-attention mechanism
- State-of-the-art for NLP and increasingly vision
- Architecture: Encoder-Decoder or Encoder-only/Decoder-only

## Transformer Variants

| Model | Type | Best For |
|-------|------|----------|
| BERT | Encoder | Understanding, classification, NER |
| GPT | Decoder | Text generation, completion |
| T5 | Encoder-Decoder | Translation, summarization |
| ViT | Encoder | Image classification |
| CLIP | Dual Encoder | Image-text matching |
| Whisper | Encoder-Decoder | Speech recognition |
| Stable Diffusion | U-Net + Attention | Image generation |

## Model Selection Guide

```
START
├── Is data tabular?
│   ├── Yes → Start with XGBoost/LightGBM
│   │         If insufficient → Try Neural Networks
│   └── No → Continue
├── Is data images?
│   ├── Yes → CNN (ResNet, EfficientNet) or ViT
│   │         For detection → YOLO, Faster R-CNN
│   └── No → Continue
├── Is data text?
│   ├── Yes → Fine-tune Transformer (BERT, RoBERTa)
│   │         For generation → GPT-style models
│   └── No → Continue
├── Is data sequential/time-series?
│   ├── Yes → Transformer or LSTM
│   │         Consider temporal fusion transformer
│   └── No → Continue
├── Is data multi-modal?
│   └── Yes → CLIP-style, Flamingo, or custom fusion
```

## Training Considerations

### Data Requirements (Rule of Thumb)

| Model Type | Minimum Samples |
|------------|-----------------|
| Linear models | 100+ |
| Tree-based | 1,000+ |
| Deep learning | 10,000+ |
| Large language models | Millions+ |

### Compute Requirements

| Model | Training | Inference |
|-------|----------|-----------|
| Logistic Regression | CPU | CPU |
| Random Forest | CPU (parallel) | CPU |
| XGBoost | CPU/GPU | CPU |
| ResNet-50 | GPU | GPU/CPU |
| BERT-base | GPU | GPU/CPU |
| GPT-3 175B | Multi-GPU cluster | Multi-GPU |
| LLaMA 70B | Multi-GPU | Multi-GPU |

## Common Metrics

### Classification
- **Accuracy**: Overall correctness (misleading with imbalanced data)
- **Precision**: TP / (TP + FP) — "Of predicted positives, how many correct?"
- **Recall**: TP / (TP + FN) — "Of actual positives, how many found?"
- **F1 Score**: Harmonic mean of precision and recall
- **AUC-ROC**: Area under ROC curve

### Regression
- **MSE**: Mean Squared Error
- **MAE**: Mean Absolute Error
- **RMSE**: Root Mean Squared Error
- **R²**: Coefficient of determination

### NLP-Specific
- **BLEU**: Translation quality
- **ROUGE**: Summarization quality
- **Perplexity**: Language model quality

## Hyperparameter Tuning

### Approaches
1. **Grid Search**: Exhaustive, slow
2. **Random Search**: Often better than grid
3. **Bayesian Optimization**: Optuna, Hyperopt
4. **Population-based**: Ray Tune

### Key Hyperparameters by Model

| Model | Key Hyperparameters |
|-------|---------------------|
| Random Forest | n_estimators, max_depth, min_samples_split |
| XGBoost | learning_rate, max_depth, n_estimators |
| Neural Networks | learning_rate, batch_size, hidden_size, dropout |
| Transformers | learning_rate, warmup_steps, weight_decay |

---
*This excerpt was curated for agent knowledge grounding.*
