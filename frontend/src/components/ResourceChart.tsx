import React, { useEffect, useRef } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { Line } from 'react-chartjs-2'
import { InstanceMetrics } from '../types'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

interface ResourceChartProps {
  metrics: InstanceMetrics[]
  type: 'cpu' | 'memory' | 'disk'
  title: string
  color: string
}

const ResourceChart: React.FC<ResourceChartProps> = ({ metrics, type, title, color }) => {
  const chartRef = useRef<ChartJS<'line'>>(null)

  const getValue = (metric: InstanceMetrics) => {
    switch (type) {
      case 'cpu':
        return metric.cpu_usage
      case 'memory':
        return metric.memory_usage
      case 'disk':
        return metric.disk_usage
      default:
        return 0
    }
  }

  const data = {
    labels: metrics.map(metric =>
      new Date(metric.timestamp).toLocaleTimeString()
    ),
    datasets: [
      {
        label: title,
        data: metrics.map(getValue),
        borderColor: color,
        backgroundColor: color + '20',
        fill: true,
        tension: 0.4,
        pointRadius: 2,
        pointHoverRadius: 4,
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      intersect: false,
      mode: 'index' as const,
    },
    plugins: {
      legend: {
        display: false,
      },
      title: {
        display: true,
        text: title,
        font: {
          size: 14,
          weight: 'bold',
        },
      },
      tooltip: {
        callbacks: {
          label: function(context: any) {
            return `${title}: ${context.parsed.y.toFixed(1)}%`
          }
        }
      }
    },
    scales: {
      x: {
        display: true,
        grid: {
          display: false,
        },
        ticks: {
          maxTicksLimit: 6,
          font: {
            size: 11,
          },
        },
      },
      y: {
        display: true,
        min: 0,
        max: 100,
        grid: {
          color: '#f3f4f6',
        },
        ticks: {
          callback: function(value: any) {
            return value + '%'
          },
          font: {
            size: 11,
          },
        },
      },
    },
    animation: {
      duration: 300,
    },
  }

  return (
    <div className="bg-white rounded-lg p-4 shadow-sm border" style={{ height: '200px' }}>
      <Line ref={chartRef} data={data} options={options} />
    </div>
  )
}

export default ResourceChart
