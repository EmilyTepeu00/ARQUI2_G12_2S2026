import { useMemo } from "react";

const TOTAL_ESPACIOS = 6;
const RADIO = 1.75;
const ALTURA = 1.26;

export function EggsGroup({ espaciosLibres}){
    const ocupados = Math.max(0, Math.min(TOTAL_ESPACIOS,   TOTAL_ESPACIOS - espaciosLibres));

    const posiciones = useMemo(() => {
        return Array.from({length: TOTAL_ESPACIOS}, (_, i) => {
            const angulo = (Math.PI/2) + (i / TOTAL_ESPACIOS) * Math.PI * 2;
            return [Math.cos(angulo) * RADIO, ALTURA, Math.sin(angulo) * RADIO];
        });
    }, []);

    return (
        <group>
            {posiciones.map((pos, i) => (
                <mesh key={i} position={pos} visible={i < ocupados} scale={[1, 1.3, 1]} castShadow receiveShadow>
                    <sphereGeometry args={[0.6, 16, 16]} />
                    <meshStandardMaterial color="#f5deb3" />
                </mesh>
            ))}
        </group>
    )
}