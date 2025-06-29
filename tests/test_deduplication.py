

import pytest
from src.services.deduplication_engine import AlarmFingerprint, FingerprintStrategy, SimilarityCalculator


@pytest.fixture
def fingerprint_generator_strict():
    return AlarmFingerprint(strategy=FingerprintStrategy.STRICT)

@pytest.fixture
def fingerprint_generator_normal():
    return AlarmFingerprint(strategy=FingerprintStrategy.NORMAL)

@pytest.fixture
def fingerprint_generator_loose():
    return AlarmFingerprint(strategy=FingerprintStrategy.LOOSE)

@pytest.fixture
def similarity_calculator():
    return SimilarityCalculator()


# Test AlarmFingerprint
def test_generate_fingerprint_strict(fingerprint_generator_strict):
    alarm1 = {
        "title": "CPU Usage High",
        "host": "server-01",
        "service": "nginx",
        "severity": "critical",
        "environment": "prod"
    }
    alarm2 = {
        "title": "CPU Usage High",
        "host": "server-01",
        "service": "nginx",
        "severity": "critical",
        "environment": "prod"
    }
    alarm3 = {
        "title": "CPU Usage High",
        "host": "server-02", # Different host
        "service": "nginx",
        "severity": "critical",
        "environment": "prod"
    }
    
    assert fingerprint_generator_strict.generate_fingerprint(alarm1) == \
           fingerprint_generator_strict.generate_fingerprint(alarm2)
    assert fingerprint_generator_strict.generate_fingerprint(alarm1) != \
           fingerprint_generator_strict.generate_fingerprint(alarm3)

def test_generate_fingerprint_normal(fingerprint_generator_normal):
    alarm1 = {
        "title": "CPU Usage High on server-01 at 2025-06-29 10:00:00",
        "host": "server-01.local",
        "service": "nginx-v1.0",
        "severity": "high",
        "environment": "prod"
    }
    alarm2 = {
        "title": "CPU Usage High on server-01 at 2025-06-29 10:01:00", # Different timestamp
        "host": "server-01",
        "service": "nginx",
        "severity": "medium", # Different severity, but normalized
        "environment": "prod"
    }
    
    # Normalization should make these fingerprints the same
    assert fingerprint_generator_normal.generate_fingerprint(alarm1) == \
           fingerprint_generator_normal.generate_fingerprint(alarm2)

def test_generate_fingerprint_loose(fingerprint_generator_loose):
    alarm1 = {
        "title": "Disk Space Low on /dev/sda1",
        "host": "server-01",
        "service": "filesystem",
        "severity": "low"
    }
    alarm2 = {
        "title": "Disk Space Low on /dev/sdb2", # Different disk
        "host": "server-02", # Different host
        "service": "filesystem",
        "severity": "info"
    }
    
    # Loose strategy should focus on title and service
    # Since the disk name is different, the fingerprint should be different
    assert fingerprint_generator_loose.generate_fingerprint(alarm1) != \
           fingerprint_generator_loose.generate_fingerprint(alarm2)


# Test SimilarityCalculator
def test_calculate_text_similarity_tfidf(similarity_calculator):
    text1 = "The quick brown fox jumps over the lazy dog"
    text2 = "A quick brown fox jumps over a lazy cat"
    text3 = "Hello world"
    
    # High similarity
    sim1 = similarity_calculator._calculate_text_similarity(text1, text2)
    assert sim1 > 0.5 # Should be relatively high
    
    # Low similarity
    sim2 = similarity_calculator._calculate_text_similarity(text1, text3)
    assert sim2 < 0.2 # Should be very low
    
    # Identical texts
    sim3 = similarity_calculator._calculate_text_similarity(text1, text1)
    assert sim3 == 1.0
    
    # Empty texts
    sim4 = similarity_calculator._calculate_text_similarity("", "")
    assert sim4 == 0.0 # Or 1.0 depending on desired behavior for empty strings
    
    sim5 = similarity_calculator._calculate_text_similarity("text", "")
    assert sim5 == 0.0

def test_calculate_tags_similarity(similarity_calculator):
    tags1 = {"env": "prod", "region": "us-east", "app": "web"}
    tags2 = {"env": "prod", "region": "us-east", "app": "api"}
    tags3 = {"env": "dev", "region": "us-west"}
    
    # Two common keys with same values
    sim1 = similarity_calculator._calculate_tags_similarity(tags1, tags2)
    assert sim1 == 2/3 # (env, region) match out of 3 common keys
    
    # No common keys
    sim2 = similarity_calculator._calculate_tags_similarity(tags1, tags3)
    assert sim2 == 0.0
    
    # Identical tags
    sim3 = similarity_calculator._calculate_tags_similarity(tags1, tags1)
    assert sim3 == 1.0
    
    # Empty tags
    sim4 = similarity_calculator._calculate_tags_similarity({}, {})
    assert sim4 == 1.0
    
    sim5 = similarity_calculator._calculate_tags_similarity(tags1, {})
    assert sim5 == 0.0

def test_calculate_similarity_overall(similarity_calculator):
    alarm1 = {
        "title": "High CPU usage on web-server-01",
        "description": "CPU utilization is at 95% for the last 5 minutes",
        "host": "web-server-01",
        "service": "apache",
        "tags": {"env": "prod", "region": "us-east"}
    }
    alarm2 = {
        "title": "High CPU usage on web-server-01",
        "description": "CPU utilization is at 96% for the last 10 minutes",
        "host": "web-server-01",
        "service": "apache",
        "tags": {"env": "prod", "region": "us-east"}
    }
    alarm3 = {
        "title": "Disk space low on db-server-01",
        "description": "/dev/sda1 is 90% full",
        "host": "db-server-01",
        "service": "mysql",
        "tags": {"env": "dev", "region": "us-west"}
    }
    
    # Highly similar alarms
    sim_high = similarity_calculator.calculate_similarity(alarm1, alarm2)
    assert sim_high > 0.9
    
    # Very dissimilar alarms
    sim_low = similarity_calculator.calculate_similarity(alarm1, alarm3)
    assert sim_low < 0.25


