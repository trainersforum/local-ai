# Prompt
What's the difference between the Gemma 4 and Gemma 4 QAT Mobile (and Q4_0) collections of models?

I'm specifically interested in the E2B variant, and keeping the highest possible quality, for the lowest possible size, to run on low-end edge devices.

In the QAT Mobile collection, I see there is a "transformers" version (E2B, 2B), and a "ct" version (E2B 6B).

In the QAT Q4_0 collection, I see there is a "mobile optimized" version, along with assistant compatibility (seems to be relevant especially when using multi-token prediction).

Please explain the differences between these versions, and provide a recommendation of a version, that maximizes quality and speed, while minimizing size.

# Response
The Gemma 4 QAT (Quantization-Aware Training) models are explicitly designed to maintain high capability while drastically cutting memory footprints. Because quantization simulation was integrated into the training process itself, they perform significantly better than standard Post-Training Quantization (PTQ) baselines at the same size.

Here is the breakdown of the specific collections and variants you are looking at:

## The Mobile Collection (`transformers` vs `ct`)

Both of these formats utilize the custom **wNa8o8** mobile-optimized schema. This architecture applies targeted 2-bit compression to the token-generation layers while keeping core reasoning layers at higher precision to protect the model's capabilities. The difference lies in how they are packaged for the inference engine:

* **`transformers` version (`-mobile-transformers`)**: These are edge weights optimized for mobile use cases and formatted for the standard Hugging Face pipeline. They serve as the baseline reference for other formats and are best if you are writing custom Python scripts directly.
* **`ct` version (`-mobile-ct`)**: This stands for **Compressed Tensors**. These weights are serialized specifically for high-throughput inference engines like vLLM. They utilize a `w4a16` approach (4-bit weights with 16-bit activations) and support parameter-efficient fine-tuning (PEFT).

## The Q4_0 Collection (`mobile optimized` vs `assistant`)

The Q4_0 release is the general-purpose quantized format, available in GGUF for broad ecosystem compatibility on consumer GPUs and laptops.

* **Mobile Optimized (`wNa8o8`)**: While distributed alongside the Q4_0 models, this is a completely distinct schema. It uses static activations to pre-calculate scaling (reducing on-device workload) and optimizes KV caches. While the standard Q4_0 format drops the E2B footprint to about 3.2 GB, the Mobile Optimized schema shrinks it to roughly **1.0 GB**.
* **Assistant (`-assistant`)**: These are specialized "drafter" models used for **Speculative Decoding** (Multi-Token Prediction). When running the primary model, you run the smaller assistant alongside it. The assistant predicts multiple tokens ahead, and the primary model verifies them, which drastically accelerates text generation without losing quality.

---
> **Key insight:** The massive drop from Q4_0 to the Mobile Optimized schema comes from applying aggressive 2-bit quantization exclusively to the decoding layers, while pre-calculating scaling to ease the computational load on mobile hardware.
---

## The Recommendation

To maximize quality and speed while minimizing size on a highly constrained edge environment—whether that's a single-board computer like a Raspberry Pi Zero or a persistent terminal session via Android—the **Mobile Optimized format** is the clear winner.

1. **Size:** It brings the E2B memory footprint down to ~1.0 GB. If your use case doesn't require multimodal input, you can drop the vision and audio encoders to push the memory requirement completely under 1 GB.
2. **Quality:** By keeping the core reasoning layers at a higher precision than the token layers, the model retains its intelligence despite the aggressive compression.
3. **Speed:** Static activations reduce the active compute overhead on the device itself, saving vital processing cycles.

Unless you have the RAM to spare for a drafter model (which generally rules out low-end edge devices), skip the assistant versions and deploy the text-only mobile-optimized schema to avoid out-of-memory errors.