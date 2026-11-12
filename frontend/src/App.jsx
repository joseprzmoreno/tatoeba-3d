import React, { useState, useEffect, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Stars, Html } from '@react-three/drei';
import * as THREE from 'three';

const API_BASE = 'http://localhost:18000/api';
const VISUAL_SCALE = 50; 

const LANGUAGES = [
  { code: 'en', name: 'English' },
  { code: 'fr', name: 'French' },
  { code: 'de', name: 'German' },
  { code: 'it', name: 'Italian' },
  { code: 'pt', name: 'Portuguese' },
  { code: 'ca', name: 'Catalan' },
  { code: 'eu', name: 'Basque' },
  { code: 'el', name: 'Greek' }
];

const SentenceNode = ({ data, isSelected, onClick }) => {
  const meshRef = useRef();
  const pos = [data.x * VISUAL_SCALE, data.y * VISUAL_SCALE, data.z * VISUAL_SCALE];

  useFrame(({ clock }) => {
    if (!isSelected && meshRef.current) {
      meshRef.current.scale.setScalar(1 + Math.sin(clock.elapsedTime * 3 + data.id) * 0.15);
    }
  });

  return (
    <group position={pos}>
      <mesh 
        ref={meshRef}
        onClick={(e) => {
          e.stopPropagation();
          onClick(data);
        }}
      >
        <sphereGeometry args={[isSelected ? 0.15 : 0.05, 32, 32]} />
        <meshBasicMaterial color={isSelected ? "#ffffff" : "#00ccff"} />
      </mesh>

      {isSelected && (
        <Html zIndexRange={[100, 0]}>
          <div style={{
            background: 'rgba(15, 15, 25, 0.95)',
            border: '2px solid #444466',
            padding: '30px',
            borderRadius: '16px',
            width: '500px',
            color: 'white',
            boxShadow: '0 10px 50px rgba(0,0,0,0.9)',
            pointerEvents: 'auto',
            transform: 'translate3d(-50%, -120%, 0)'
          }}>
            <h3 style={{ margin: '0 0 20px 0', fontSize: '2.5rem', color: '#aaddff', lineHeight: '1.2' }}>
              {data.text}
            </h3>
            {data.translated_text ? (
              <p style={{ margin: 0, fontSize: '2.0rem', color: '#cccccc', lineHeight: '1.2', fontStyle: 'italic' }}>
                {data.translated_text}
              </p>
            ) : (
              <p style={{ margin: 0, fontSize: '2.0rem', color: '#888888', fontStyle: 'italic' }}>
                Translating...
              </p>
            )}
          </div>
        </Html>
      )}
    </group>
  );
};

const CameraRig = ({ target }) => {
  useFrame((state) => {
    if (target) {
      const targetVec = new THREE.Vector3(
        target.x * VISUAL_SCALE, 
        target.y * VISUAL_SCALE, 
        target.z * VISUAL_SCALE
      );
      const idealCameraPos = targetVec.clone().add(new THREE.Vector3(0, 2, 10));
      
      state.camera.position.lerp(idealCameraPos, 0.08);
      state.controls?.target.lerp(targetVec, 0.08);
      state.camera.lookAt(targetVec);
    }
  });
  return null;
};

export default function App() {
  const [nodes, setNodes] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [targetLang, setTargetLang] = useState('en');
  
  const debounceTimer = useRef(null);

  // Updated to handle accumulating new nodes for endless exploration
  const fetchNearby = async (x, y, z, isNewJump = false) => {
    try {
      const res = await fetch(`${API_BASE}/sentences/nearby?x=${x}&y=${y}&z=${z}&radius=10.0`);
      const data = await res.json();
      
      setNodes(prevNodes => {
        // If it's a completely new random jump, clear the old universe
        if (isNewJump) return data;
        
        // Otherwise, map over the existing nodes and append the newly discovered ones 
        // that aren't already drawn on the screen.
        const nodeMap = new Map(prevNodes.map(n => [n.id, n]));
        data.forEach(n => nodeMap.set(n.id, n));
        return Array.from(nodeMap.values());
      });
      
      if (isNewJump && data.length > 0) {
        handleNodeSelect(data[0]);
      }
    } catch (err) {
      console.error("Failed to fetch nearby sentences:", err);
    }
  };

  const executeTranslation = async (nodeToFetch, lang) => {
    try {
      const res = await fetch(`${API_BASE}/sentences/${nodeToFetch.id}?lang=${lang}`);
      const detailedData = await res.json();
      
      setSelectedNode(detailedData);
      
      // Fetch the next cluster based on this new location and append them (isNewJump = false)
      fetchNearby(detailedData.x, detailedData.y, detailedData.z, false);
    } catch (err) {
      console.error("Failed to fetch sentence details:", err);
    }
  };

  const handleNodeSelect = (node) => {
    setSelectedNode({ ...node, translated_text: null });
    
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }
    
    debounceTimer.current = setTimeout(() => {
      executeTranslation(node, targetLang);
    }, 500);
  };

const jumpToRandomCoordinate = async () => {
    // Clear the current selection to reset the UI
    setSelectedNode(null);
    
    try {
      // 1. Ask the database for a guaranteed real sentence
      const res = await fetch(`${API_BASE}/sentences/random`);
      const randomSentence = await res.json();
      
      // 2. Fetch the cluster around its exact coordinates. 
      // The 'true' flag ensures the app auto-selects this exact sentence and pans the camera to it.
      fetchNearby(randomSentence.x, randomSentence.y, randomSentence.z, true); 
    } catch (err) {
      console.error("Failed to fetch a random sentence:", err);
    }
  };

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (!selectedNode || nodes.length === 0) return;
      
      const currentIndex = nodes.findIndex(n => n.id === selectedNode.id);
      let nextIndex = currentIndex;

      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        nextIndex = (currentIndex + 1) % nodes.length;
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        nextIndex = (currentIndex - 1 + nodes.length) % nodes.length;
      }

      if (nextIndex !== currentIndex && nextIndex >= 0) {
        handleNodeSelect(nodes[nextIndex]);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedNode, nodes, targetLang]);

  useEffect(() => {
    if (selectedNode && selectedNode.target_lang !== targetLang && selectedNode.translated_text) {
      handleNodeSelect(selectedNode);
    }
  }, [targetLang]);

  useEffect(() => {
    jumpToRandomCoordinate();
  }, []);

  return (
    <>
      <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', zIndex: 10, pointerEvents: 'none' }}>
        <header style={{ padding: '20px', display: 'flex', justifyContent: 'space-between', pointerEvents: 'auto' }}>
          <h1 style={{ margin: 0, fontSize: '1.5rem', color: '#fff' }}>tatoeba-3d</h1>
          <div style={{ display: 'flex', gap: '10px' }}>
            <select 
              value={targetLang} 
              onChange={(e) => setTargetLang(e.target.value)}
              style={{ background: '#2a2a40', color: 'white', padding: '10px', borderRadius: '8px' }}
            >
              {LANGUAGES.map(lang => (
                <option key={lang.code} value={lang.code}>{lang.name}</option>
              ))}
            </select>
            <button 
              onClick={(e) => {
                e.target.blur(); // Drops focus from the button immediately
                jumpToRandomCoordinate();
              }}
              style={{ background: '#2a2a40', color: 'white', padding: '10px 20px', borderRadius: '8px', cursor: 'pointer' }}
            >
              Coordenada aleatoria
            </button>
          </div>
        </header>
      </div>

      <Canvas camera={{ position: [0, 0, 15], fov: 60 }}>
        <color attach="background" args={['#050510']} />
        
        <Stars radius={150} depth={50} count={10000} factor={4} fade speed={1} />
        
        <CameraRig target={selectedNode} />
        <OrbitControls makeDefault enablePan={false} maxDistance={100} />

        {nodes.map((node) => (
          <SentenceNode 
            key={node.id} 
            data={selectedNode?.id === node.id ? selectedNode : node} 
            isSelected={selectedNode?.id === node.id}
            onClick={() => handleNodeSelect(node)}
          />
        ))}
      </Canvas>
    </>
  );
}