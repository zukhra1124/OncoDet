"""
Grad-CAM implementation for DenseNet121.

The idea (from Selvaraju et al., ICCV 2017) is:
- Do a forward pass and grab activations at the last conv layer
- Backpropagate the target class score to get gradients at that layer
- Average the gradients across spatial dims to get per-channel weights
- Weighted-sum the activation maps, ReLU it, and you get a heatmap
  showing which parts of the image the model focused on

This is really important for medical imaging because doctors need to
see WHY the model made a particular prediction, not just what it predicted.
"""

import cv2
import torch
import numpy as np
from PIL import Image
from models.model_loader import get_model, get_device
from config import IMAGE_SIZE


class GradCAM:
    """
    Hooks into the last DenseBlock of DenseNet121 to capture
    activations and gradients, then produces a heatmap.
    """

    def __init__(self, model=None):
        self.model = model or get_model()
        self.device = get_device()
        self.activations = None
        self.gradients = None
        self._register_hooks()

    def _register_hooks(self):
        """Set up forward/backward hooks on denseblock4."""
        target_layer = self.model.densenet.features.denseblock4

        def forward_hook(module, input, output):
            self.activations = output.detach()

        def backward_hook(module, grad_input, grad_output):
            self.gradients = grad_output[0].detach()

        target_layer.register_forward_hook(forward_hook)
        target_layer.register_full_backward_hook(backward_hook)

    def generate(self, image_tensor, target_class=None):
        """
        Generate the raw heatmap for a given image.
        If target_class is None, we explain whatever class the model predicted.
        Returns a 224x224 numpy array with values in [0, 1].
        """
        self.model.eval()
        image_tensor = image_tensor.to(self.device)
        image_tensor.requires_grad_(True)

        output = self.model(image_tensor)

        if target_class is None:
            target_class = output.argmax(dim=1).item()

        self.model.zero_grad()

        # backprop from the target class score
        target_score = output[0, target_class]
        target_score.backward()

        gradients = self.gradients[0]       # shape: (C, H, W)
        activations = self.activations[0]   # shape: (C, H, W)

        # channel importance = global average of each gradient map
        weights = torch.mean(gradients, dim=(1, 2))

        # weighted combination of activation maps
        cam = torch.sum(weights[:, None, None] * activations, dim=0)

        # only keep positive contributions
        cam = torch.relu(cam)

        # normalise to 0-1 range
        cam = cam.cpu().numpy()
        if cam.max() > 0:
            cam = cam / cam.max()

        # resize to match the input image dimensions
        cam = cv2.resize(cam, (IMAGE_SIZE, IMAGE_SIZE))

        return cam

    def generate_overlay(self, image_tensor, original_pil_image, target_class=None):
        """
        Make the heatmap and blend it on top of the original image.
        Returns both the overlay and the standalone heatmap as PIL images.
        """
        heatmap = self.generate(image_tensor, target_class)

        original_resized = original_pil_image.resize((IMAGE_SIZE, IMAGE_SIZE))
        original_np = np.array(original_resized)

        # apply JET colourmap to the heatmap
        heatmap_colored = cv2.applyColorMap(
            np.uint8(255 * heatmap), cv2.COLORMAP_JET
        )
        heatmap_colored = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB)

        # blend: 40% heatmap + 60% original
        overlay = np.float32(heatmap_colored) * 0.4 + np.float32(original_np) * 0.6
        overlay = np.clip(overlay, 0, 255).astype(np.uint8)

        overlay_image = Image.fromarray(overlay)
        heatmap_image = Image.fromarray(heatmap_colored)

        return overlay_image, heatmap_image
