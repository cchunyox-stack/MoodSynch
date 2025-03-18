import time
import board
import neopixel

# Initialize NeoPixel strip on GPIO pin D18 with 55 LEDs
pixels = neopixel.NeoPixel(board.D18, 55, brightness=1)

def set_emotion_color(emotion):
    if emotion == "Positive":
        return (255, 255, 0)  # Yellow
    elif emotion == "Focused":
        return (0, 0, 255)    # Blue
    elif emotion == "Negative":
        return (0, 255, 0)    # Green
    else:
        return (0, 0, 0)      # Turn off LEDs if emotion is unknown

def show_emotion(emotion):
    color = set_emotion_color(emotion)
    pixels.fill(color)

def main():
    # Example emotions for testing
    emotions = ["Positive", "Focused", "Negative"]

    for emotion in emotions:
        show_emotion(emotion)
        time.sleep(2)  # Display each emotion for 2 seconds

    pixels.fill((0, 0, 0))  # Turn off LEDs after displaying emotions

if __name__ == "__main__":
    main()