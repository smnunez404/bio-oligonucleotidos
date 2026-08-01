import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { InfoTip } from "./InfoTip";

const BASE_COLOR: Record<string, number> = {
  A: 0xe74c3c,
  T: 0x3498db,
  U: 0x3498db,
  G: 0x2ecc71,
  C: 0xf1c40f,
};

interface Props {
  sequence: string; // wild-type, sentido del transcrito
  variantIndex: number; // posición (0-based) de la base mutada
  mutantBase: string;
}

/**
 * Representación esquemática (ilustrativa) de una doble hélice de ADN,
 * generada a partir de la secuencia real, con geometría de ADN-B idealizada
 * (no medida). A diferencia de la proteína (PDB 7M1Q, estructura real
 * medida por crio-EM), esto NO es un dato experimental — es un dibujo para
 * hacer tangible "es una doble hebra, y un solo par de bases cambia".
 */
export function DnaHelix3D({ sequence, variantIndex, mutantBase }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const width = container.clientWidth;
    const height = 420;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);

    scene.add(new THREE.AmbientLight(0xffffff, 0.7));
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(10, 20, 10);
    scene.add(dirLight);

    // --- Geometría helicoidal idealizada (parámetros de ADN-B) ---
    const N = Math.min(sequence.length, 60); // recorte para que no se sature visualmente
    const start = Math.max(0, Math.min(variantIndex - N / 2, sequence.length - N));
    const radius = 3.2;
    const rise = 1.3; // "altura" por par de bases (unidades de escena, no Å reales)
    const twistPerBase = (2 * Math.PI) / 10; // ~10 pb por vuelta, como el ADN-B real

    const group = new THREE.Group();
    const sphereGeo = new THREE.SphereGeometry(0.35, 12, 12);
    const backboneMat1 = new THREE.MeshStandardMaterial({ color: 0x9aa0a6 });
    const backboneMat2 = new THREE.MeshStandardMaterial({ color: 0x6b7280 });

    for (let k = 0; k < N; k++) {
      const i = start + k;
      const base = sequence[i]?.toUpperCase() ?? "N";
      const angle = k * twistPerBase;
      const y = k * rise - (N * rise) / 2;

      const x1 = radius * Math.cos(angle);
      const z1 = radius * Math.sin(angle);
      const x2 = radius * Math.cos(angle + Math.PI);
      const z2 = radius * Math.sin(angle + Math.PI);

      const isVariant = i === variantIndex;

      const s1 = new THREE.Mesh(sphereGeo, backboneMat1);
      s1.position.set(x1, y, z1);
      group.add(s1);

      const s2 = new THREE.Mesh(sphereGeo, backboneMat2);
      s2.position.set(x2, y, z2);
      group.add(s2);

      // "Escalón" (par de bases) uniendo las dos hebras, coloreado por nucleótido.
      const rungColor = isVariant ? 0xffffff : BASE_COLOR[base] ?? 0x888888;
      const dist = Math.hypot(x2 - x1, z2 - z1);
      const cylGeo = new THREE.CylinderGeometry(
        isVariant ? 0.16 : 0.09,
        isVariant ? 0.16 : 0.09,
        dist,
        8
      );
      const cylMat = new THREE.MeshStandardMaterial({
        color: rungColor,
        emissive: isVariant ? 0xff3366 : 0x000000,
        emissiveIntensity: isVariant ? 0.6 : 0,
      });
      const cyl = new THREE.Mesh(cylGeo, cylMat);
      cyl.position.set((x1 + x2) / 2, y, (z1 + z2) / 2);
      cyl.lookAt(new THREE.Vector3(x2, y, z2));
      cyl.rotateX(Math.PI / 2);
      group.add(cyl);
    }

    scene.add(group);

    camera.position.set(0, 0, 16);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 1.2;

    let frameId: number;
    function animate() {
      frameId = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    }
    animate();

    function onResize() {
      if (!container) return;
      const w = container.clientWidth;
      camera.aspect = w / height;
      camera.updateProjectionMatrix();
      renderer.setSize(w, height);
    }
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(frameId);
      window.removeEventListener("resize", onResize);
      controls.dispose();
      renderer.dispose();
      sphereGeo.dispose();
      group.traverse((obj) => {
        if (obj instanceof THREE.Mesh) {
          obj.geometry.dispose();
          if (Array.isArray(obj.material)) {
            obj.material.forEach((m) => m.dispose());
          } else {
            obj.material.dispose();
          }
        }
      });
      container.removeChild(renderer.domElement);
    };
  }, [sequence, variantIndex, mutantBase]);

  return (
    <div className="card">
      <h2>Doble hélice de ADN — representación esquemática</h2>
      <p className="muted">
        Generada a partir de la secuencia real, con geometría de{" "}
        <InfoTip text="El ADN normalmente no es una escalera recta: las dos hebras se enroscan una sobre la otra en forma de espiral (~10 pares de bases por vuelta completa). Esta forma se llama 'ADN-B' y es la más común en el cuerpo.">
          ADN-B
        </InfoTip>{" "}
        idealizada — <strong>no es una estructura medida</strong> (a
        diferencia de la proteína, que sí lo es). Es para hacer tangible que
        el ADN es de doble hebra, y que la mutación es un solo escalón
        (resaltado en blanco/rosa) distinto entre las dos versiones. Arrastrá
        para rotar, scroll para zoom.
      </p>
      <div
        ref={containerRef}
        style={{ width: "100%", height: "420px", borderRadius: "8px", overflow: "hidden" }}
      />
      <div className="legend">
        <span className="legend-item">
          <span className="swatch" style={{ background: "#e74c3c" }} /> A
        </span>
        <span className="legend-item">
          <span className="swatch" style={{ background: "#3498db" }} /> T/U
        </span>
        <span className="legend-item">
          <span className="swatch" style={{ background: "#2ecc71" }} /> G
        </span>
        <span className="legend-item">
          <span className="swatch" style={{ background: "#f1c40f" }} /> C
        </span>
        <span className="legend-item">
          <span className="swatch" style={{ background: "#ffffff", border: "1px solid #999" }} />{" "}
          posición de la mutación
        </span>
      </div>
    </div>
  );
}
