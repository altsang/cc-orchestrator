/**
 * @jest-environment jsdom
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import StatusIndicator from '../../components/StatusIndicator'
import { InstanceStatus } from '../../types'

describe('StatusIndicator', () => {
  it('renders RUNNING status correctly', () => {
    render(<StatusIndicator status={InstanceStatus.RUNNING} />)
    expect(screen.getByText('Running')).toBeInTheDocument()
  })

  it('renders STOPPED status correctly', () => {
    render(<StatusIndicator status={InstanceStatus.STOPPED} />)
    expect(screen.getByText('Stopped')).toBeInTheDocument()
  })

  it('renders INITIALIZING status correctly', () => {
    render(<StatusIndicator status={InstanceStatus.INITIALIZING} />)
    expect(screen.getByText('Initializing')).toBeInTheDocument()
  })

  it('renders ERROR status correctly', () => {
    render(<StatusIndicator status={InstanceStatus.ERROR} />)
    expect(screen.getByText('Error')).toBeInTheDocument()
  })

  it('applies correct CSS classes for RUNNING status', () => {
    render(<StatusIndicator status={InstanceStatus.RUNNING} />)
    const indicator = screen.getByText('Running').parentElement
    expect(indicator).toHaveClass('bg-green-100', 'text-green-800')
  })

  it('applies correct CSS classes for ERROR status', () => {
    render(<StatusIndicator status={InstanceStatus.ERROR} />)
    const indicator = screen.getByText('Error').parentElement
    expect(indicator).toHaveClass('bg-red-100', 'text-red-800')
  })

  it('shows indicator dot', () => {
    render(<StatusIndicator status={InstanceStatus.RUNNING} />)
    const dot = screen.getByText('Running').parentElement?.querySelector('.w-2.h-2')
    expect(dot).toBeInTheDocument()
  })
})
