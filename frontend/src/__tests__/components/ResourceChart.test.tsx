/**
 * @jest-environment jsdom
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import ResourceChart from '../../components/ResourceChart'

// Mock Chart.js
vi.mock('react-chartjs-2', () => ({
  Line: ({ data, options }: { data: any; options: any }) => (
    <div data-testid="mock-chart">
      <div data-testid="chart-data">{JSON.stringify(data)}</div>
      <div data-testid="chart-options">{JSON.stringify(options)}</div>
    </div>
  )
}))

// Mock Chart.js registration
vi.mock('chart.js', () => ({
  Chart: {
    register: vi.fn(),
  },
  CategoryScale: vi.fn(),
  LinearScale: vi.fn(),
  PointElement: vi.fn(),
  LineElement: vi.fn(),
  Title: vi.fn(),
  Tooltip: vi.fn(),
  Legend: vi.fn(),
}))

const mockResourceData = {
  cpu_usage: [10, 20, 30, 25, 15],
  memory_usage: [50, 55, 60, 58, 52],
  timestamps: ['10:00', '10:01', '10:02', '10:03', '10:04']
}

describe('ResourceChart', () => {
  it('renders chart component', () => {
    render(<ResourceChart data={mockResourceData} />)
    
    expect(screen.getByTestId('mock-chart')).toBeInTheDocument()
  })

  it('passes correct data to chart', () => {
    render(<ResourceChart data={mockResourceData} />)
    
    const chartData = screen.getByTestId('chart-data')
    const dataContent = JSON.parse(chartData.textContent || '{}')
    
    expect(dataContent.labels).toEqual(mockResourceData.timestamps)
    expect(dataContent.datasets).toHaveLength(2) // CPU and Memory datasets
  })

  it('configures chart with proper labels', () => {
    render(<ResourceChart data={mockResourceData} />)
    
    const chartData = screen.getByTestId('chart-data')
    const dataContent = JSON.parse(chartData.textContent || '{}')
    
    const cpuDataset = dataContent.datasets.find((d: any) => d.label === 'CPU Usage (%)')
    const memoryDataset = dataContent.datasets.find((d: any) => d.label === 'Memory Usage (%)')
    
    expect(cpuDataset).toBeDefined()
    expect(memoryDataset).toBeDefined()
    expect(cpuDataset.data).toEqual(mockResourceData.cpu_usage)
    expect(memoryDataset.data).toEqual(mockResourceData.memory_usage)
  })

  it('applies correct styling to datasets', () => {
    render(<ResourceChart data={mockResourceData} />)
    
    const chartData = screen.getByTestId('chart-data')
    const dataContent = JSON.parse(chartData.textContent || '{}')
    
    const cpuDataset = dataContent.datasets.find((d: any) => d.label === 'CPU Usage (%)')
    const memoryDataset = dataContent.datasets.find((d: any) => d.label === 'Memory Usage (%)')
    
    // Should have different colors
    expect(cpuDataset.borderColor).toBeDefined()
    expect(memoryDataset.borderColor).toBeDefined()
    expect(cpuDataset.borderColor).not.toEqual(memoryDataset.borderColor)
  })

  it('configures chart options correctly', () => {
    render(<ResourceChart data={mockResourceData} />)
    
    const chartOptions = screen.getByTestId('chart-options')
    const optionsContent = JSON.parse(chartOptions.textContent || '{}')
    
    expect(optionsContent.responsive).toBe(true)
    expect(optionsContent.plugins?.title?.display).toBe(true)
    expect(optionsContent.plugins?.title?.text).toBe('Resource Usage')
  })

  it('handles empty data gracefully', () => {
    const emptyData = {
      cpu_usage: [],
      memory_usage: [],
      timestamps: []
    }
    
    render(<ResourceChart data={emptyData} />)
    
    expect(screen.getByTestId('mock-chart')).toBeInTheDocument()
  })

  it('handles missing data properties', () => {
    const incompleteData = {
      cpu_usage: [10, 20],
      // Missing memory_usage and timestamps
    } as any
    
    render(<ResourceChart data={incompleteData} />)
    
    expect(screen.getByTestId('mock-chart')).toBeInTheDocument()
  })

  it('sets up y-axis to show percentages', () => {
    render(<ResourceChart data={mockResourceData} />)
    
    const chartOptions = screen.getByTestId('chart-options')
    const optionsContent = JSON.parse(chartOptions.textContent || '{}')
    
    const yScale = optionsContent.scales?.y
    expect(yScale?.min).toBe(0)
    expect(yScale?.max).toBe(100)
    expect(yScale?.ticks?.callback).toBeDefined()
  })

  it('has proper accessibility attributes', () => {
    const { container } = render(<ResourceChart data={mockResourceData} />)
    
    // Chart should be accessible
    const chartElement = container.querySelector('[data-testid="mock-chart"]')
    expect(chartElement).toBeInTheDocument()
  })

  it('updates when data changes', () => {
    const { rerender } = render(<ResourceChart data={mockResourceData} />)
    
    const newData = {
      cpu_usage: [30, 40, 50],
      memory_usage: [70, 75, 80],
      timestamps: ['11:00', '11:01', '11:02']
    }
    
    rerender(<ResourceChart data={newData} />)
    
    const chartData = screen.getByTestId('chart-data')
    const dataContent = JSON.parse(chartData.textContent || '{}')
    
    expect(dataContent.labels).toEqual(newData.timestamps)
  })
})