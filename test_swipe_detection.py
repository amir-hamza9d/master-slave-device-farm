#!/usr/bin/env python3
"""
Test script to validate swipe detection logic
This script simulates the swipe detection logic to help debug threshold issues
"""

import math
import time

def calculate_distance(x1, y1, x2, y2):
    """Calculate distance between two points"""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

def is_swipe_gesture(start_x, start_y, end_x, end_y, start_time, end_time, threshold_distance, threshold_time):
    """Determine if movement qualifies as a swipe gesture"""
    if start_x is None or start_y is None or end_x is None or end_y is None:
        return False
    
    distance = calculate_distance(start_x, start_y, end_x, end_y)
    duration = end_time - start_time
    
    return distance >= threshold_distance and duration >= threshold_time

def test_swipe_scenarios():
    """Test various swipe scenarios"""
    print("🧪 Testing Swipe Detection Logic")
    print("=" * 50)
    
    # Test scenarios based on typical Android raw coordinates
    test_cases = [
        # (start_x, start_y, end_x, end_y, duration_ms, description)
        (16140, 31743, 19114, 7864, 500, "Long swipe up-right"),
        (1000, 2000, 1050, 2050, 150, "Short movement"),
        (5000, 10000, 8000, 15000, 300, "Medium diagonal swipe"),
        (10000, 20000, 10000, 15000, 200, "Vertical swipe up"),
        (15000, 10000, 20000, 10000, 250, "Horizontal swipe right"),
        (1000, 1000, 1010, 1010, 50, "Very short tap-like movement"),
        (0, 0, 100, 100, 1000, "Slow small movement"),
    ]
    
    # Current thresholds
    threshold_distance = 200  # Updated threshold
    threshold_time = 50       # Updated threshold
    
    print(f"Thresholds: distance >= {threshold_distance}, time >= {threshold_time}ms")
    print()
    
    for i, (start_x, start_y, end_x, end_y, duration, description) in enumerate(test_cases, 1):
        start_time = 1000.0  # Mock start time
        end_time = start_time + duration
        
        distance = calculate_distance(start_x, start_y, end_x, end_y)
        is_swipe = is_swipe_gesture(start_x, start_y, end_x, end_y, start_time, end_time, threshold_distance, threshold_time)
        
        result = "SWIPE" if is_swipe else "TAP"
        distance_check = "✅" if distance >= threshold_distance else "❌"
        time_check = "✅" if duration >= threshold_time else "❌"
        
        print(f"Test {i}: {description}")
        print(f"  Coordinates: ({start_x}, {start_y}) → ({end_x}, {end_y})")
        print(f"  Distance: {distance:.1f} {distance_check} (>= {threshold_distance})")
        print(f"  Duration: {duration}ms {time_check} (>= {threshold_time}ms)")
        print(f"  Result: {result}")
        print()

if __name__ == "__main__":
    test_swipe_scenarios()
