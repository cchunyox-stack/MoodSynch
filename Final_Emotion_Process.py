#File to determine final emotion
import cv2
from deepface import DeepFace
import threading
from PIL import Image, ImageTk
import customtkinter
import tkinter as tk
import time
import pygame
import pygame.time
import random
import os
import pandas as pd

import queue
import joblib

emotion_queue = queue.Queue()

def process_predictions(q):
    # Extract predictions from the queue
    facial_probs = q.get()
    hrv_probs = q.get()
    gsr_probs = q.get()

    focused_probs_mean = (facial_probs[0] + hrv_probs[0] + gsr_probs[0]) / 3
    negative_probs_mean = (facial_probs[1] + hrv_probs[1] + gsr_probs[1]) / 3
    psoitive_probs_mean = (facial_probs[2] + hrv_probs[2] + gsr_probs[2]) / 3
    # Combine the probabilities into a DataFrame
    data = pd.DataFrame({
        'Focused_Conf':focused_probs_mean,
        'Negative_Conf': negative_probs_mean,
        'Positive_Conf': psoitive_probs_mean
    }, index = [0])
    print(data)

    data_mean = data.mean()
    data_mean = data_mean.values.reshape(-1,1)
    # Load SVM model for emotion prediction
    emotion_svm = joblib.load("C:\\Users\\crist\\Downloads\\MoodSynch\\emotion_svm_model.joblib")

    # Assuming you already have X_train and Y_train from your previous dataset
    # Train the SVM model on X_train and Y_train

    # Predict emotions using the trained SVM model
    predicted_emotion = emotion_svm.predict(data)
    print(predicted_emotion[0])

    return predicted_emotion[0]