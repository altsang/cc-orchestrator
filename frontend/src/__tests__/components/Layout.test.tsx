/**
 * @jest-environment jsdom
 */
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import Layout from '../../components/Layout'

const TestWrapper = ({ children }: { children: React.ReactNode }) => {
  return (
    <BrowserRouter>
      {children}
    </BrowserRouter>
  )
}

describe('Layout', () => {
  it('renders the main layout structure', () => {
    render(
      <TestWrapper>
        <Layout>
          <div>Test Content</div>
        </Layout>
      </TestWrapper>
    )
    
    expect(screen.getByText('Test Content')).toBeInTheDocument()
  })

  it('renders the header with title', () => {
    render(
      <TestWrapper>
        <Layout>
          <div>Test Content</div>
        </Layout>
      </TestWrapper>
    )
    
    expect(screen.getByText('CC-Orchestrator Dashboard')).toBeInTheDocument()
  })

  it('renders navigation menu', () => {
    render(
      <TestWrapper>
        <Layout>
          <div>Test Content</div>
        </Layout>
      </TestWrapper>
    )
    
    // Should have navigation links
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Instances')).toBeInTheDocument()
  })

  it('has responsive design classes', () => {
    const { container } = render(
      <TestWrapper>
        <Layout>
          <div>Test Content</div>
        </Layout>
      </TestWrapper>
    )
    
    // Should have responsive utility classes
    const layoutElements = container.querySelectorAll('[class*="sm:"], [class*="md:"], [class*="lg:"]')
    expect(layoutElements.length).toBeGreaterThan(0)
  })

  it('renders footer information', () => {
    render(
      <TestWrapper>
        <Layout>
          <div>Test Content</div>
        </Layout>
      </TestWrapper>
    )
    
    // Should have some footer content
    const footer = screen.getByRole('contentinfo') || screen.getByText(/CC-Orchestrator/i)
    expect(footer).toBeInTheDocument()
  })

  it('has proper semantic HTML structure', () => {
    render(
      <TestWrapper>
        <Layout>
          <div>Test Content</div>
        </Layout>
      </TestWrapper>
    )
    
    // Should have proper semantic elements
    expect(screen.getByRole('banner')).toBeInTheDocument() // header
    expect(screen.getByRole('main')).toBeInTheDocument() // main content area
  })

  it('children are rendered in the main content area', () => {
    const testContent = 'Unique Test Content 12345'
    
    render(
      <TestWrapper>
        <Layout>
          <div>{testContent}</div>
        </Layout>
      </TestWrapper>
    )
    
    expect(screen.getByText(testContent)).toBeInTheDocument()
    
    // Should be within main element
    const mainElement = screen.getByRole('main')
    expect(mainElement).toContainElement(screen.getByText(testContent))
  })
})