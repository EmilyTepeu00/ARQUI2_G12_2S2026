import { Suspense, useRef, useState, useEffect } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { ModeloHuevera } from "./IncubadoraScene";
import * as THREE from "three";

const COLOR_FRIO = new THREE.Color("#38bdf8");
const COLOR_NORMAL = new THREE.Color("#34d399");
const COLOR_CALIENTE = new THREE.Color("#f87171");

function colorPorTemperatura(temp){
    if (temp == null) return COLOR_NORMAL;
    if (temp < 37){
        const t = THREE.MathUtils.clamp((37 - temp) / 5, 0, 1); //Hasta 3°C por debajo
        return new THREE.Color().lerpColors(COLOR_NORMAL, COLOR_FRIO, t);
    }
    if (temp > 38) {
        const t = THREE.MathUtils.clamp((temp - 38) / 5, 0, 1); //Hasta 3°C por encima
        return new THREE.Color().lerpColors(COLOR_NORMAL, COLOR_CALIENTE, t);
    }
    return COLOR_NORMAL
}

export function IncubadoraViz({ temperatura, rotacionActiva, espaciosLibres }){
    const [colorLuz, setColorLuz] = useState('#34d399');

    useEffect(() => {
        setColorLuz(colorPorTemperatura(temperatura));
    }, [temperatura]);

    return(
        <div className="h-96 rounded-2x1 border border-slate-800 bg-slate-900/40">
            <Canvas camera={{ position: [-0.5,3,4.5] }} shadows>
                <ambientLight intensity={0.8} />
                <directionalLight
                    color={colorLuz}
                    position={[-8,10,0]}
                    intensity={3}
                    castShadow
                    shadow-mapSize={[1024, 1024]}
                />
                <Suspense fallback={null}>
                    <ModeloHuevera position={[0, -0.5, 0]} temperatura={temperatura} rotacionActiva={rotacionActiva} espaciosLibres={espaciosLibres} />
                </Suspense>
                <OrbitControls />
            </Canvas>
        </div>
    )
}