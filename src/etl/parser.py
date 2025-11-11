"""
Clean ETL Pipeline for Julius Caesar
Parses raw JSON → structured speeches → enhanced chunks

Usage:
    python -m src.etl.parser --input data/raw/julius-caesar.json --output data/processed/chunks.jsonl
"""
import json
import re
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional


class JuliusCaesarParser:
    """Parse Julius Caesar from raw Folger Shakespeare JSON"""
    
    # Character names from the play
    CHARACTERS = {
        'FLAVIUS', 'MARULLUS', 'CARPENTER', 'COBBLER', 'CAESAR', 'CALPHURNIA',
        'BRUTUS', 'PORTIA', 'LUCIUS', 'CASSIUS', 'CASCA', 'CINNA', 'DECIUS',
        'LIGARIUS', 'METELLUS', 'CIMBER', 'TREBONIUS', 'CICERO', 'PUBLIUS',
        'POPILIUS', 'LENA', 'ANTONY', 'LEPIDUS', 'OCTAVIUS', 'SERVANT',
        'SOOTHSAYER', 'ARTEMIDORUS', 'LUCILIUS', 'TITINIUS', 'MESSALA',
        'VARRO', 'CLAUDIUS', 'CATO', 'STRATO', 'VOLUMNIUS', 'DARDANUS',
        'CLITUS', 'PINDARUS', 'FIRST', 'SECOND', 'THIRD', 'FOURTH', 'BOTH',
        'PLEBEIAN', 'PLEBEIANS', 'SOLDIER', 'SOLDIERS', 'MESSENGER', 'POET',
        'COMMONER', 'COMMONERS', 'CITIZENS', 'SENATORS', 'ALL'
    }
    
    def __init__(self):
        self.speeches = []
        self.current_act = None
        self.current_scene = None
        
    def clean_text(self, text: str) -> str:
        """Clean raw text by removing FTLN numbers and normalizing whitespace"""
        # Remove FTLN line numbers
        text = re.sub(r'FTLN\s+\d+', '', text)
        # Remove page headers like "11 Julius Caesar ACT 1. SC. 1"
        text = re.sub(r'\d+\s+Julius Caesar\s+ACT\s+\d+\.\s+SC\.\s+\d+', '', text)
        # Remove standalone numbers (line numbers)
        text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
        # Remove stage directions in brackets
        text = re.sub(r'\[.*?\]', '', text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def is_valid_speaker(self, name: str) -> bool:
        """Check if name is a valid character"""
        name = name.upper().strip()
        return any(char in name or name in char for char in self.CHARACTERS)
    
    def parse_page(self, page_text: str) -> None:
        """Parse a single page and extract speeches"""
        # Clean the text
        text = self.clean_text(page_text)
        
        # Detect ACT marker
        act_match = re.search(r'ACT\s+(\d+)', text, re.IGNORECASE)
        if act_match:
            self.current_act = int(act_match.group(1))
            print(f"  ✓ Act {self.current_act}")
        
        # Detect Scene marker
        scene_match = re.search(r'Scene\s+(\d+)', text, re.IGNORECASE)
        if scene_match:
            self.current_scene = int(scene_match.group(1))
            print(f"    → Scene {self.current_scene}")
        
        # Skip if no act/scene yet
        if not self.current_act:
            return
        
        # Find all speaker patterns: SPEAKER_NAME followed by dialogue
        # Pattern: ALL CAPS name at start or after newline/period
        pattern = r'\b([A-Z][A-Z\s]{2,25}?)\b\s+([A-Z][a-z]|\bO\b|\bAy\b|\bNo\b|\bWhat\b|\bWhy\b|\bHow\b|\bI\b)'
        
        matches = list(re.finditer(pattern, text))
        
        for i, match in enumerate(matches):
            speaker = match.group(1).strip()
            
            # Validate speaker
            if not self.is_valid_speaker(speaker):
                continue
            
            # Extract dialogue from this speaker to next speaker
            start_pos = match.start(2)  # Start from the dialogue
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            
            dialogue = text[start_pos:end_pos].strip()
            
            # Clean dialogue
            # Remove stage directions
            dialogue = re.sub(r'\b(Enter|Exit|Exeunt|Re-enter|Aside|They exit|He exits|She exits|All exit).*?\.', '', dialogue, flags=re.IGNORECASE)
            dialogue = re.sub(r'\(.*?\)', '', dialogue)  # Remove parentheticals
            dialogue = ' '.join(dialogue.split())  # Normalize whitespace
            
            # Only save substantial speeches
            if len(dialogue) > 25 and not dialogue.startswith(('ACT', 'Scene', 'Enter', 'Exit')):
                self.speeches.append({
                    'act': self.current_act,
                    'scene': self.current_scene,
                    'speaker': speaker,
                    'text': dialogue
                })
    
    def parse_json(self, input_path: str) -> List[Dict]:
        """Parse the entire Julius Caesar JSON file"""
        print(f"📖 Parsing Julius Caesar from {input_path}")
        
        with open(input_path, 'r', encoding='utf-8') as f:
            pages = json.load(f)
        
        # Process pages 9+ (actual play starts at page 9)
        for page_obj in pages:
            page_num = page_obj.get('page', 0)
            if page_num >= 9:
                self.parse_page(page_obj.get('raw', ''))
        
        print(f"\n✅ Extracted {len(self.speeches)} speeches")
        print(f"   Acts: {sorted(set(s['act'] for s in self.speeches))}")
        print(f"   Unique speakers: {len(set(s['speaker'] for s in self.speeches))}")
        
        return self.speeches


class HybridChunker:
    """
    Hybrid Semantic-Structural Chunking Strategy
    
    Three-tier approach:
    1. Scene summaries (macro context)
    2. Speech units (main retrieval - soliloquies, major speeches, dialogue exchanges)
    3. Famous quotes (micro retrieval)
    """
    
    # Famous quotes to extract
    FAMOUS_QUOTES = [
        ("Beware the ides of March", "SOOTHSAYER", 1, 2),
        ("Et tu, Brute", "CAESAR", 3, 1),
        ("Friends, Romans, countrymen", "ANTONY", 3, 2),
        ("This was the noblest Roman", "ANTONY", 5, 5),
        ("Cowards die many times", "CAESAR", 2, 2),
        ("The fault, dear Brutus, is not in our stars", "CASSIUS", 1, 2),
        ("Cry 'Havoc!' and let slip the dogs of war", "ANTONY", 3, 1),
    ]
    
    def __init__(self, speeches: List[Dict]):
        self.speeches = speeches
        self.chunks = []
        
    def group_by_scene(self) -> Dict[Tuple[int, int], List[Dict]]:
        """Group speeches by (act, scene)"""
        scenes = {}
        for speech in self.speeches:
            key = (speech['act'], speech['scene'])
            if key not in scenes:
                scenes[key] = []
            scenes[key].append(speech)
        return scenes
    
    def create_scene_summary(self, act: int, scene: int, speeches: List[Dict]) -> Dict:
        """Create TIER 1: Scene summary chunk"""
        speakers = sorted(set(s['speaker'] for s in speeches))
        
        # Get first speech for preview
        preview = speeches[0]['text'][:200] if speeches else ""
        
        return {
            'chunk_id': f'A{act}S{scene}-summary',
            'chunk_type': 'scene_summary',
            'act': act,
            'scene': scene,
            'text': f"Act {act}, Scene {scene}: This scene features {', '.join(speakers[:5])}{'...' if len(speakers) > 5 else ''}. Total of {len(speeches)} speeches. Opening: {preview}...",
            'speakers': speakers,
            'num_speeches': len(speeches),
            'total_words': sum(len(s['text'].split()) for s in speeches)
        }
    
    def is_soliloquy(self, speech: Dict, scene_speeches: List[Dict]) -> bool:
        """Determine if a speech is a soliloquy (single speaker, substantial length)"""
        word_count = len(speech['text'].split())
        
        # Check if this speaker dominates the scene
        speaker_count = sum(1 for s in scene_speeches if s['speaker'] == speech['speaker'])
        
        return word_count > 100 and speaker_count == 1
    
    def is_major_speech(self, speech: Dict) -> bool:
        """Identify major speeches (e.g., Antony's funeral oration)"""
        word_count = len(speech['text'].split())
        text_lower = speech['text'].lower()
        
        # Antony's funeral speech
        if 'friends, romans, countrymen' in text_lower and word_count > 150:
            return True
        
        # Brutus's funeral speech
        if speech['speaker'] == 'BRUTUS' and speech['act'] == 3 and speech['scene'] == 2 and word_count > 100:
            return True
        
        # Other long speeches
        return word_count > 200
    
    def create_speech_chunk(self, speech: Dict, chunk_type: str, idx: int) -> Dict:
        """Create TIER 2: Speech unit chunk"""
        return {
            'chunk_id': f"A{speech['act']}S{speech['scene']}-{speech['speaker'].lower()}-{chunk_type}-{idx:03d}",
            'chunk_type': chunk_type,
            'act': speech['act'],
            'scene': speech['scene'],
            'speaker': speech['speaker'],
            'text': f"{speech['speaker']}: {speech['text']}",
            'is_soliloquy': chunk_type == 'soliloquy',
            'word_count': len(speech['text'].split())
        }
    
    def create_dialogue_chunk(self, speeches: List[Dict], idx: int) -> Dict:
        """Create TIER 2: Dialogue exchange chunk"""
        act = speeches[0]['act']
        scene = speeches[0]['scene']
        speakers = [s['speaker'] for s in speeches]
        
        # Combine dialogue
        dialogue = ' '.join([f"{s['speaker']}: {s['text']}" for s in speeches])
        
        return {
            'chunk_id': f"A{act}S{scene}-exchange-{idx:03d}",
            'chunk_type': 'dialogue_exchange',
            'act': act,
            'scene': scene,
            'speakers': speakers,
            'text': dialogue,
            'turn_count': len(speeches),
            'word_count': len(dialogue.split())
        }
    
    def create_chunks(self) -> List[Dict]:
        """Create all three tiers of chunks"""
        print("\n🔨 Creating hybrid semantic-structural chunks...")
        
        scenes = self.group_by_scene()
        
        # Process each scene
        for (act, scene), scene_speeches in sorted(scenes.items()):
            # TIER 1: Scene summary
            summary = self.create_scene_summary(act, scene, scene_speeches)
            self.chunks.append(summary)
            
            # TIER 2: Process speeches
            speech_idx = 0
            exchange_buffer = []
            exchange_idx = 0
            
            for speech in scene_speeches:
                # Check if soliloquy
                if self.is_soliloquy(speech, scene_speeches):
                    # Flush exchange buffer
                    if exchange_buffer:
                        self.chunks.append(self.create_dialogue_chunk(exchange_buffer, exchange_idx))
                        exchange_buffer = []
                        exchange_idx += 1
                    
                    # Add soliloquy
                    self.chunks.append(self.create_speech_chunk(speech, 'soliloquy', speech_idx))
                    speech_idx += 1
                
                # Check if major speech
                elif self.is_major_speech(speech):
                    # Flush exchange buffer
                    if exchange_buffer:
                        self.chunks.append(self.create_dialogue_chunk(exchange_buffer, exchange_idx))
                        exchange_buffer = []
                        exchange_idx += 1
                    
                    # Add major speech
                    self.chunks.append(self.create_speech_chunk(speech, 'major_speech', speech_idx))
                    speech_idx += 1
                
                # Regular dialogue - add to exchange buffer
                else:
                    exchange_buffer.append(speech)
                    
                    # Flush if exchange gets too long (5+ turns or 500+ words)
                    if len(exchange_buffer) >= 5 or sum(len(s['text'].split()) for s in exchange_buffer) > 500:
                        self.chunks.append(self.create_dialogue_chunk(exchange_buffer, exchange_idx))
                        exchange_buffer = []
                        exchange_idx += 1
            
            # Flush remaining exchange
            if exchange_buffer:
                self.chunks.append(self.create_dialogue_chunk(exchange_buffer, exchange_idx))
        
        # TIER 3: Add famous quotes
        for quote_text, speaker, act, scene in self.FAMOUS_QUOTES:
            # Find the speech containing this quote
            for speech in self.speeches:
                if (speech['act'] == act and speech['scene'] == scene and 
                    speech['speaker'] == speaker and quote_text.lower() in speech['text'].lower()):
                    
                    self.chunks.append({
                        'chunk_id': f"A{act}S{scene}-quote-{speaker.lower()}",
                        'chunk_type': 'famous_quote',
                        'act': act,
                        'scene': scene,
                        'speaker': speaker,
                        'text': f"{speaker}: {quote_text}",
                        'is_famous_quote': True,
                        'word_count': len(quote_text.split())
                    })
                    break
        
        print(f"✅ Created {len(self.chunks)} chunks")
        print(f"   Scene summaries: {len([c for c in self.chunks if c['chunk_type'] == 'scene_summary'])}")
        print(f"   Soliloquies: {len([c for c in self.chunks if c['chunk_type'] == 'soliloquy'])}")
        print(f"   Major speeches: {len([c for c in self.chunks if c['chunk_type'] == 'major_speech'])}")
        print(f"   Dialogue exchanges: {len([c for c in self.chunks if c['chunk_type'] == 'dialogue_exchange'])}")
        print(f"   Famous quotes: {len([c for c in self.chunks if c['chunk_type'] == 'famous_quote'])}")
        
        return self.chunks


def main():
    parser = argparse.ArgumentParser(description='Parse Julius Caesar with hybrid chunking')
    parser.add_argument('--input', required=True, help='Input raw JSON file')
    parser.add_argument('--output', required=True, help='Output chunks JSONL file')
    args = parser.parse_args()
    
    # Ensure output directory exists
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    
    # Parse speeches
    parser = JuliusCaesarParser()
    speeches = parser.parse_json(args.input)
    
    # Create chunks
    chunker = HybridChunker(speeches)
    chunks = chunker.create_chunks()
    
    # Save chunks
    with open(args.output, 'w', encoding='utf-8') as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
    
    print(f"\n💾 Saved to: {args.output}")


if __name__ == '__main__':
    main()
