#!/usr/bin/env python3
"""
Ověření závislostí pro cloud deployment
Test jestli aktuální setup bude fungovat na serveru bez conda
"""

import sys
import importlib
import subprocess

def test_imports():
    """Test všech kritických importů"""
    print("🔍 Testing critical imports...")
    
    critical_packages = [
        ('flask', 'Flask'),
        ('mediapipe', 'MediaPipe pose detection'),
        ('cv2', 'OpenCV'),
        ('numpy', 'NumPy'),
        ('matplotlib', 'Matplotlib'),
        ('openpyxl', 'Excel export'),
        ('PIL', 'Pillow/PIL'),
        ('tqdm', 'Progress bars')
    ]
    
    all_good = True
    
    for package, description in critical_packages:
        try:
            module = importlib.import_module(package)
            version = getattr(module, '__version__', 'unknown')
            print(f"   ✅ {description}: {version}")
        except ImportError as e:
            print(f"   ❌ {description}: MISSING - {e}")
            all_good = False
    
    return all_good

def test_mediapipe_functionality():
    """Test MediaPipe základní funkčnost"""
    print("\n🤖 Testing MediaPipe functionality...")
    
    try:
        import mediapipe as mp
        import cv2
        import numpy as np
        
        # Initialize MediaPipe pose
        mp_pose = mp.solutions.pose
        pose = mp_pose.Pose(
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Test s dummy image
        dummy_image = np.zeros((480, 640, 3), dtype=np.uint8)
        results = pose.process(cv2.cvtColor(dummy_image, cv2.COLOR_BGR2RGB))
        
        print("   ✅ MediaPipe Pose initialization: OK")
        print("   ✅ Dummy image processing: OK")
        
        pose.close()
        return True
        
    except Exception as e:
        print(f"   ❌ MediaPipe test failed: {e}")
        return False

def test_python_version():
    """Test Python verze"""
    print(f"\n🐍 Python version check...")
    
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    print(f"   Current: Python {version_str}")
    
    if version.major == 3 and version.minor == 9:
        print("   ✅ Python 3.9 - Compatible with MediaPipe")
        return True
    else:
        print("   ⚠️  Not Python 3.9 - May cause MediaPipe issues on deployment")
        return False

def generate_deployment_requirements():
    """Vytvoří deployment-ready requirements.txt"""
    print(f"\n📝 Generating deployment requirements...")
    
    try:
        # Get exact installed versions
        result = subprocess.run([sys.executable, '-m', 'pip', 'freeze'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            all_packages = result.stdout.strip().split('\n')
            
            # Critical packages for deployment
            critical = [
                'Flask', 'Werkzeug', 'mediapipe', 'opencv-python', 
                'numpy', 'matplotlib', 'tqdm', 'openpyxl', 'requests', 'Pillow'
            ]
            
            deployment_reqs = []
            for pkg_line in all_packages:
                if '==' in pkg_line:
                    pkg_name = pkg_line.split('==')[0]
                    if any(crit.lower() == pkg_name.lower() for crit in critical):
                        deployment_reqs.append(pkg_line)
            
            with open('requirements-deployment.txt', 'w') as f:
                f.write('\n'.join(sorted(deployment_reqs)) + '\n')
            
            print("   ✅ Created requirements-deployment.txt")
            print(f"   📦 {len(deployment_reqs)} critical packages")
            
            for req in deployment_reqs:
                print(f"      - {req}")
            
            return True
        else:
            print(f"   ❌ Failed to get pip freeze: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error generating requirements: {e}")
        return False

def main():
    print("🚀 DEPENDENCY VERIFICATION FOR CLOUD DEPLOYMENT")
    print("=" * 55)
    
    # Check current environment
    conda_env = sys.executable
    if 'trunk_analysis' in conda_env:
        print(f"✅ Running in trunk_analysis environment")
        print(f"   Python path: {conda_env}")
    else:
        print(f"⚠️  Not in trunk_analysis environment")
        print(f"   Python path: {conda_env}")
        print(f"   Please run: conda activate trunk_analysis")
    
    print("-" * 55)
    
    # Run tests
    tests = [
        ("Import Test", test_imports),
        ("Python Version", test_python_version), 
        ("MediaPipe Functionality", test_mediapipe_functionality),
        ("Deployment Requirements", generate_deployment_requirements)
    ]
    
    all_passed = True
    for test_name, test_func in tests:
        print(f"\n🔧 {test_name}")
        if not test_func():
            all_passed = False
    
    print(f"\n" + "=" * 55)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Your setup is ready for cloud deployment")
        print("📁 Use requirements-deployment.txt for deployment")
        
        print(f"\n🚀 Recommended deployment platforms:")
        print("   1. Railway: railway up")
        print("   2. Render: Use render-fixed.yaml") 
        print("   3. DigitalOcean: Use .do/app.yaml")
        
    else:
        print("💥 SOME TESTS FAILED!")
        print("❌ Fix issues before deployment")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)