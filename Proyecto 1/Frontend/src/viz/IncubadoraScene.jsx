import { useEffect, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { useGLTF } from "@react-three/drei";
import { EggsGroup } from "./EggsGroup";

const ANGULO_MAX = THREE.MathUtils.degToRad(45);
const VELOCIDAD_GIRO = 1.7;
const ESCALA_MODELO = 35;
const POSICION_MODELO = [0,1,0];


export function ModeloHuevera({ temperatura, espaciosLibres, rotacionActiva }) {
    const meshRef = useRef();
    const ladoRef = useRef(1);      //1 = +45°, -1 = -45°
    const rotacionAnteriorRef = useRef(false);
    const { scene } = useGLTF("/models/huevera.glb");

    useEffect(() => {
        if (rotacionActiva && !rotacionAnteriorRef.current){
            ladoRef.current *= -1;
        }
        rotacionAnteriorRef.current = rotacionActiva;
    }, [rotacionActiva]);

    scene.traverse((child) => {
        if (child.isMesh && child.material){
            if(!child.userData._materialClonado){
                child.material = child.material.clone();
                child.material.metalness = 0;
                child.material.roughness = 0.6;
                child.userData._materialClonado = true;
            }
            child.material.color.set("#2e2e2e");
        }
        if (child.isMesh) {
            child.geometry.computeVertexNormals();
            child.material.flatShading = false;
            child.material.needsUpdate = true;
        }
    });

    useFrame((state, delta) => {
        if (!meshRef.current) return;
        const deltaSeguro = Math.min(delta, 0.05);

        if(rotacionActiva){
            const anguloObjetivo = ANGULO_MAX * ladoRef.current;
            meshRef.current.rotation.z = THREE.MathUtils.lerp(
                meshRef.current.rotation.z,
                anguloObjetivo,
                deltaSeguro * VELOCIDAD_GIRO
            );
        }
    });

    return (
        <group ref={meshRef}>
            <primitive object={scene} scale={ESCALA_MODELO} position={POSICION_MODELO} />
            <EggsGroup espaciosLibres={espaciosLibres} />
        </group>
    );
}