type SparklineProps = {
  values: number[];
  color: string;
  width?: number;
  height?: number;
};

/** Mini-graphique d'evolution (memes dimensions/inline-svg que les maquettes), a partir
 * de vraies valeurs (pas d'exemple fixe) : normalise les points sur la hauteur donnee. */
export function Sparkline({ values, color, width = 64, height = 20 }: SparklineProps) {
  const viewW = width;
  const viewH = height;
  const max = Math.max(...values, 0);
  const min = Math.min(...values, 0);
  const range = max - min || 1;
  const step = viewW / Math.max(values.length - 1, 1);

  const points = values
    .map((v, i) => {
      const x = i * step;
      const y = viewH - 2 - ((v - min) / range) * (viewH - 4);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg className="spark" width={width} height={height} viewBox={`0 0 ${viewW} ${viewH}`} preserveAspectRatio="none">
      <polyline fill="none" stroke={color} strokeWidth="2" points={points}></polyline>
    </svg>
  );
}
