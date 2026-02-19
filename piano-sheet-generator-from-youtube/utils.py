import cv2
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim

def compare_frames(frame1, frame2):
    """
    Compare two frames using Structural Similarity Index (SSIM).
    Returns a score between 0 and 1. (1 is identical)
    """
    # Convert frames to grayscale if they are not already
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    
    # Compute SSIM
    score, _ = ssim(gray1, gray2, full=True)
    return score

def crop_black_bars(image):
    """
    Automatically crops black bars from an image.
    Expects a PIL Image object.
    """
    # Convert PIL Image to OpenCV format
    cv_img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    
    # Threshold to find non-black areas
    _, thresh = cv2.threshold(gray, 15, 255, cv2.THRESH_BINARY)
    
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return image
    
    # Find the largest contour which should be the content
    c = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(c)
    
    # Crop and return as PIL Image
    return image.crop((x, y, x + w, y + h))

def is_similar(frame1, frame2, threshold=0.98):
    """
    Check if two frames are similar enough to be considered the same page.
    """
    score = compare_frames(frame1, frame2)
    return score > threshold
