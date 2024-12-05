"""
基本测试示例
"""
import pytest

print("Loading test file...")

def test_example():
    """一个简单的示例测试用例"""
    print("Running test_example")
    assert True

def test_addition():
    """测试基本的加法运算"""
    print("Running test_addition")
    assert 1 + 1 == 2

if __name__ == '__main__':
    pytest.main(['-v']) 