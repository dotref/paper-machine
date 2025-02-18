import hashlib
import os
from typing import Dict, List, Set
from pathlib import Path
import random
import string

"""
A simple block deduplicator, we may also consider calling available deduplication tools
"""
class BlockDeduplicator:
    def __init__(self, block_size: int = 4096):
        """
        Initialize deduplicator with specified block size.
        
        Args:
            block_size: Size of each block in bytes (default 4KB)
        """
        self.block_size = block_size
        self.block_hashes: Dict[str, bytes] = {}  # Maps hash to block content
        self.file_blocks: Dict[str, List[str]] = {}  # Maps filename to list of block hashes
        self.storage_path = Path("deduplicated_storage")
        self.storage_path.mkdir(exist_ok=True)

    def _calculate_block_hash(self, block: bytes) -> str:
        """Calculate SHA-256 hash of a block."""
        return hashlib.sha256(block).hexdigest()

    def store_file(self, filepath: str) -> None:
        """
        Store a file using block-level deduplication.
        
        Args:
            filepath: Path to the file to be stored
        """
        file_blocks: List[str] = []
        
        with open(filepath, 'rb') as f:
            while True:
                block = f.read(self.block_size)
                if not block:
                    break
                    
                # Calculate block hash
                block_hash = self._calculate_block_hash(block)
                file_blocks.append(block_hash)
                
                # Store block if it's new
                if block_hash not in self.block_hashes:
                    self.block_hashes[block_hash] = block
                    # Write block to storage
                    with open(self.storage_path / block_hash, 'wb') as block_file:
                        block_file.write(block)
        
        # Store file's block list
        self.file_blocks[filepath] = file_blocks

    def restore_file(self, filepath: str, output_path: str) -> None:
        """
        Restore a file from deduplicated storage.
        
        Args:
            filepath: Original filepath used during storage
            output_path: Where to restore the file
        """
        if filepath not in self.file_blocks:
            raise ValueError(f"File {filepath} not found in storage")
            
        with open(output_path, 'wb') as f:
            for block_hash in self.file_blocks[filepath]:
                # Read block from storage
                with open(self.storage_path / block_hash, 'rb') as block_file:
                    block = block_file.read()
                f.write(block)

    def get_storage_savings(self) -> dict:
        """Calculate storage savings from deduplication."""
        total_blocks = sum(len(blocks) for blocks in self.file_blocks.values())
        unique_blocks = len(self.block_hashes)
        saved_blocks = total_blocks - unique_blocks
        
        return {
            'total_blocks': total_blocks,
            'unique_blocks': unique_blocks,
            'saved_blocks': saved_blocks,
            'space_saved_bytes': saved_blocks * self.block_size
        }

#####################################################################
############################## Testing ##############################
#####################################################################

def create_test_files():
    """Create test files with controlled duplicate content"""
    shared_content = ''.join(random.choices(string.ascii_letters, k=10000))
    
    with open('file1.txt', 'w') as f:
        f.write(shared_content)
        f.write("\nUnique content for file 1")
    
    with open('file2.txt', 'w') as f:
        f.write(shared_content)
        f.write("\nUnique content for file 2")
    
    with open('file3.txt', 'w') as f:
        f.write(''.join(random.choices(string.ascii_letters, k=10000)))

def test_basic_deduplication():
    print("\n=== Testing Basic Deduplication ===")
    # Create test files
    create_test_files()
    
    # Initialize deduplicator
    dedup = BlockDeduplicator(block_size=4096)
    
    # Store all test files
    files = ['file1.txt', 'file2.txt', 'file3.txt']
    original_sizes = {}
    
    print("Original file sizes:")
    for file in files:
        size = os.path.getsize(file)
        original_sizes[file] = size
        print(f"{file}: {size} bytes")
        dedup.store_file(file)
    
    # Get deduplication statistics
    stats = dedup.get_storage_savings()
    print("\nDeduplication statistics:")
    print(f"Total blocks: {stats['total_blocks']}")
    print(f"Unique blocks: {stats['unique_blocks']}")
    print(f"Blocks saved: {stats['saved_blocks']}")
    print(f"Space saved: {stats['space_saved_bytes']} bytes")
    
    # Restore and verify
    print("\nRestoring and verifying files:")
    for file in files:
        restored_path = f"restored_{file}"
        dedup.restore_file(file, restored_path)
        
        with open(file, 'rb') as f1, open(restored_path, 'rb') as f2:
            original_content = f1.read()
            restored_content = f2.read()
            matches = original_content == restored_content
            print(f"{file}: {'✓ Content matches' if matches else '✗ Content differs'}")

    # Clean up
    for file in files:
        os.remove(file)
        os.remove(f"restored_{file}")

def test_edge_cases():
    print("\n=== Testing Edge Cases ===")
    dedup = BlockDeduplicator(block_size=4096)
    
    # Test empty file
    print("Testing empty file...")
    with open('empty.txt', 'w') as f:
        pass
    
    # Test small file
    print("Testing small file...")
    with open('small.txt', 'w') as f:
        f.write('Hello')
    
    # Test file smaller than block size
    print("Testing sub-block size file...")
    with open('subblock.txt', 'w') as f:
        f.write('A' * 2048)
    
    # Test file exactly block size
    print("Testing exact block size file...")
    with open('exactblock.txt', 'w') as f:
        f.write('B' * 4096)
    
    files = ['empty.txt', 'small.txt', 'subblock.txt', 'exactblock.txt']
    
    for file in files:
        dedup.store_file(file)
        dedup.restore_file(file, f'restored_{file}')
        
        # Verify contents
        with open(file, 'rb') as f1, open(f'restored_{file}', 'rb') as f2:
            content_matches = f1.read() == f2.read()
            print(f"{file}: {'✓ Content matches' if content_matches else '✗ Content differs'}")
        
        # Clean up
        os.remove(file)
        os.remove(f'restored_{file}')

def test_real_world_scenario():
    print("\n=== Testing Real World Scenario ===")
    dedup = BlockDeduplicator(block_size=4096)
    
    # Create some sample files with similar content
    print("Creating sample files with similar content...")
    text1 = "This is a test file with some content.\n" * 1000
    text2 = "This is a test file with some content.\nWith an extra line\n" * 1000
    
    with open('real_file1.txt', 'w') as f:
        f.write(text1)
    with open('real_file2.txt', 'w') as f:
        f.write(text2)
    
    # Store and analyze
    print("\nStoring files...")
    dedup.store_file('real_file1.txt')
    dedup.store_file('real_file2.txt')
    
    # Print storage savings
    stats = dedup.get_storage_savings()
    print(f"Storage savings: {stats['space_saved_bytes'] / 1024:.2f} KB")
    
    # Restore and verify
    print("\nRestoring and verifying files...")
    dedup.restore_file('real_file1.txt', 'restored_real_file1.txt')
    dedup.restore_file('real_file2.txt', 'restored_real_file2.txt')
    
    # Verify contents
    for file in ['real_file1.txt', 'real_file2.txt']:
        with open(file, 'rb') as f1, open(f'restored_{file}', 'rb') as f2:
            content_matches = f1.read() == f2.read()
            print(f"{file}: {'✓ Content matches' if content_matches else '✗ Content differs'}")
    
    # Clean up
    for file in ['real_file1.txt', 'real_file2.txt']:
        os.remove(file)
        os.remove(f'restored_{file}')

def test_deduplication_effectiveness():
    print("\n=== Testing Deduplication Effectiveness ===")
    
    # Create a fresh deduplicator with clean storage
    dedup = BlockDeduplicator(block_size=4096)
    # Ensure storage is clean
    if dedup.storage_path.exists():
        for file in dedup.storage_path.glob('*'):
            file.unlink()
    
    # Create two files with identical content in the middle
    # Make content exactly 3 blocks (12288 bytes) for easier tracking
    content1 = b"A" * 4096 + b"SAME" * 1024 + b"C" * 4096  # 3 blocks
    content2 = b"D" * 4096 + b"SAME" * 1024 + b"F" * 4096  # 3 blocks
    
    # Write test files
    with open('dup_test1.txt', 'wb') as f:
        f.write(content1)
    with open('dup_test2.txt', 'wb') as f:
        f.write(content2)
    
    print("\nFile sizes:")
    print(f"dup_test1.txt: {os.path.getsize('dup_test1.txt')} bytes")
    print(f"dup_test2.txt: {os.path.getsize('dup_test2.txt')} bytes")
    
    # Store both files
    dedup.store_file('dup_test1.txt')
    dedup.store_file('dup_test2.txt')
    
    # Verify deduplication
    print("\nVerifying deduplication:")
    
    # 1. Count actual unique blocks in storage
    stored_blocks = len(os.listdir(dedup.storage_path))
    print(f"Number of stored blocks: {stored_blocks}")
    
    # 2. Count total blocks in files
    total_blocks = len(dedup.file_blocks['dup_test1.txt']) + len(dedup.file_blocks['dup_test2.txt'])
    print(f"Total blocks in files: {total_blocks}")
    
    # Print block hashes for debugging
    print("\nBlock hashes for file 1:", dedup.file_blocks['dup_test1.txt'])
    print("Block hashes for file 2:", dedup.file_blocks['dup_test2.txt'])
    
    # Expected: 5 unique blocks (2 unique start blocks + 1 shared middle block + 2 unique end blocks)
    expected_blocks = 5
    dedup_occurred = stored_blocks == expected_blocks
    print(f"\nDeduplication occurred: {'✓' if dedup_occurred else '✗'}")
    print(f"Expected {expected_blocks} blocks, got {stored_blocks} blocks")
    
    # Check middle block hashes
    blocks1 = dedup.file_blocks['dup_test1.txt']
    blocks2 = dedup.file_blocks['dup_test2.txt']
    
    # The middle blocks should be identical
    middle_blocks_identical = (blocks1[1] == blocks2[1])
    print(f"Middle blocks share same hash: {'✓' if middle_blocks_identical else '✗'}")
    
    # Verify unique blocks are different
    start_blocks_different = blocks1[0] != blocks2[0]
    end_blocks_different = blocks1[2] != blocks2[2]
    print(f"Start blocks are different: {'✓' if start_blocks_different else '✗'}")
    print(f"End blocks are different: {'✓' if end_blocks_different else '✗'}")
    
    # Clean up test files
    os.remove('dup_test1.txt')
    os.remove('dup_test2.txt')
    
    # Clean up storage
    for file in dedup.storage_path.glob('*'):
        file.unlink()
    dedup.storage_path.rmdir()
    
    return all([
        dedup_occurred,
        middle_blocks_identical,
        start_blocks_different,
        end_blocks_different
    ])

def test_identical_files():
    print("\n=== Testing Identical Files Deduplication ===")
    
    # Create a fresh deduplicator with clean storage
    dedup = BlockDeduplicator(block_size=4096)
    # Ensure storage is clean
    if dedup.storage_path.exists():
        for file in dedup.storage_path.glob('*'):
            file.unlink()
    
    # Create two files with exactly the same content
    content = b"This is test content.\n" * 1000  # Make it larger than one block
    
    print(f"Creating two identical files of size: {len(content)} bytes")
    print(f"Number of full blocks expected: {len(content) // dedup.block_size}")
    
    # Write identical content to different files
    with open('identical1.txt', 'wb') as f:
        f.write(content)
    with open('identical2.txt', 'wb') as f:
        f.write(content)
    
    # Store both files
    dedup.store_file('identical1.txt')
    dedup.store_file('identical2.txt')
    
    # Verify deduplication
    print("\nVerifying deduplication:")
    
    # Count actual blocks in storage
    stored_blocks = len(os.listdir(dedup.storage_path))
    print(f"Number of stored blocks: {stored_blocks}")
    
    # Count total blocks referenced by files
    total_blocks = len(dedup.file_blocks['identical1.txt']) + len(dedup.file_blocks['identical2.txt'])
    print(f"Total block references in files: {total_blocks}")
    
    # Print block hashes for both files
    print("\nBlock hashes for file 1:", dedup.file_blocks['identical1.txt'])
    print("Block hashes for file 2:", dedup.file_blocks['identical2.txt'])
    
    # Check if all blocks are identical between files
    blocks_identical = dedup.file_blocks['identical1.txt'] == dedup.file_blocks['identical2.txt']
    print(f"\nAll blocks identical between files: {'✓' if blocks_identical else '✗'}")
    
    # Check perfect deduplication (stored blocks should equal blocks in one file)
    perfect_dedup = stored_blocks == len(dedup.file_blocks['identical1.txt'])
    print(f"Perfect deduplication achieved: {'✓' if perfect_dedup else '✗'}")
    
    if perfect_dedup:
        print(f"Storage efficiency: 50% (storing {stored_blocks} blocks instead of {total_blocks})")
    
    # Restore and verify content
    dedup.restore_file('identical1.txt', 'restored_identical1.txt')
    dedup.restore_file('identical2.txt', 'restored_identical2.txt')
    
    # Verify restored content
    with open('identical1.txt', 'rb') as f1, open('restored_identical1.txt', 'rb') as f2:
        content_matches1 = f1.read() == f2.read()
    with open('identical2.txt', 'rb') as f1, open('restored_identical2.txt', 'rb') as f2:
        content_matches2 = f1.read() == f2.read()
        
    print(f"\nRestored content matches:")
    print(f"File 1: {'✓' if content_matches1 else '✗'}")
    print(f"File 2: {'✓' if content_matches2 else '✗'}")
    
    # Clean up test files
    for file in ['identical1.txt', 'identical2.txt', 'restored_identical1.txt', 'restored_identical2.txt']:
        os.remove(file)
    
    # Clean up storage
    for file in dedup.storage_path.glob('*'):
        file.unlink()
    dedup.storage_path.rmdir()
    
    return all([blocks_identical, perfect_dedup, content_matches1, content_matches2])


def cleanup_storage(dedup):
    """Clean up the storage directory"""
    print("\nCleaning up storage...")
    for block_file in os.listdir(dedup.storage_path):
        os.remove(os.path.join(dedup.storage_path, block_file))
    os.rmdir(dedup.storage_path)

def main():
    try:
        # Run all tests
        test_basic_deduplication()
        test_edge_cases()
        test_real_world_scenario()
        # Run the new focused deduplication test
        dedup_success = test_deduplication_effectiveness()
        
        if dedup_success:
            print("\n✓ Deduplication test passed successfully!")
        else:
            print("\n✗ Deduplication test failed!")
        
        # Run the identical files test
        dedup_success = test_identical_files()
        
        if dedup_success:
            print("\n✓ Identical files deduplication test passed successfully!")
        else:
            print("\n✗ Identical files deduplication test failed!")
        
        # Clean up storage
        dedup = BlockDeduplicator()
        cleanup_storage(dedup)
                
    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()