# CC-Orchestrator Frontend

A modern React TypeScript dashboard for managing Claude Code instances, tasks, and monitoring system health in real-time.

## Features

- **Real-time Dashboard**: Live monitoring of Claude instances and tasks
- **WebSocket Integration**: Real-time updates via WebSocket connections
- **Responsive Design**: Optimized for desktop, tablet, and mobile devices
- **Interactive Management**: Start, stop, and manage Claude instances
- **Task Coordination**: Assign and track tasks across instances
- **Health Monitoring**: System health and alert management
- **Modern UI**: Clean, professional interface with Tailwind CSS

## Technology Stack

- **React 19** with TypeScript for type safety
- **Tailwind CSS** for modern, responsive styling
- **Axios** for HTTP API communication
- **WebSocket API** for real-time updates
- **React Hot Toast** for user notifications
- **Comprehensive test suite** with Jest and React Testing Library

## Getting Started

### Prerequisites

- Node.js 16+ and npm
- CC-Orchestrator backend running on `http://localhost:8080`

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
# Start development server
npm start

# Run tests
npm test

# Build for production
npm run build

# Type check
npm run type-check
```

The app will be available at `http://localhost:3000`.

## Configuration

Environment variables in `.env`:

```env
REACT_APP_API_URL=http://localhost:8080
REACT_APP_WS_URL=ws://localhost:8080/ws
REACT_APP_ENV=development
REACT_APP_DEBUG=true
```

## Architecture

### Components

- **Dashboard**: Main dashboard with tabbed interface
- **InstanceCard**: Display and manage Claude instances
- **TaskCard**: Task management and assignment
- **StatusBadge**: Reusable status indicators
- **MobileMenu**: Responsive navigation
- **Real-time components**: WebSocket-powered live updates

### Services

- **API Service**: HTTP client for backend communication
- **WebSocket Service**: Real-time event handling
- **Custom Hooks**: Data fetching and state management

### Key Files

```
frontend/
├── src/
│   ├── components/          # React components
│   │   ├── Dashboard.tsx    # Main dashboard
│   │   ├── InstanceCard.tsx # Instance management
│   │   ├── TaskCard.tsx     # Task management
│   │   └── __tests__/       # Component tests
│   ├── services/           # API and WebSocket clients
│   │   ├── api.ts          # HTTP API service
│   │   └── websocket.ts    # WebSocket service
│   ├── hooks/              # Custom React hooks
│   │   ├── useApi.ts       # API data hooks
│   │   └── useWebSocket.ts # WebSocket hooks
│   ├── types/              # TypeScript definitions
│   │   └── index.ts        # All type definitions
│   └── utils/              # Utility functions
├── public/                 # Static assets
└── package.json           # Dependencies and scripts
```

## API Integration

The frontend integrates with the FastAPI backend via:

### REST API Endpoints
- `/api/v1/instances/` - CRUD operations for instances
- `/api/v1/tasks/` - Task management
- `/api/v1/worktrees/` - Worktree operations
- `/api/v1/health/` - Health monitoring
- `/api/v1/alerts/` - Alert management

### WebSocket Endpoints
- `/ws/connect` - General WebSocket connection
- `/ws/dashboard` - Dashboard real-time updates
- `/ws/instances/{id}` - Instance-specific updates
- `/ws/tasks/{id}` - Task-specific updates
- `/ws/logs` - Log streaming

## Features in Detail

### Real-time Updates

The dashboard automatically receives and displays:
- Instance status changes
- Task progress updates
- System health alerts
- Configuration changes

### Responsive Design

- **Desktop**: Full-featured dashboard with sidebar navigation
- **Tablet**: Optimized layout with collapsible elements
- **Mobile**: Touch-friendly interface with mobile menu

### Instance Management

- View all Claude instances with status indicators
- Start/stop instances with one click
- Monitor health and performance metrics
- View detailed instance information

### Task Management

- Create and assign tasks to instances
- Track task progress and completion
- Set priorities and due dates
- View task results and metadata

### System Monitoring

- Real-time system health indicators
- Performance metrics and statistics
- Alert notifications for critical issues
- Connection status monitoring

## Testing

The frontend includes comprehensive tests:

```bash
# Run all tests
npm test

# Run tests in watch mode (default)
npm test

# Generate coverage report
npm test -- --coverage --watchAll=false
```

Test coverage includes:
- Component rendering and interactions
- API service functionality
- WebSocket connection handling
- Custom hooks behavior
- Integration tests

## Development Guidelines

### Code Style

- TypeScript strict mode enabled
- ESLint and Prettier for code formatting
- Component-based architecture
- Custom hooks for reusable logic

### State Management

- Local state with React hooks
- Custom hooks for API data
- Real-time state updates via WebSocket
- Optimistic UI updates where appropriate

### Error Handling

- Graceful error boundaries
- User-friendly error messages
- Retry mechanisms for failed requests
- Offline state handling

## Deployment

### Production Build

```bash
npm run build:prod
```

Creates optimized production build in `build/` directory.

### Environment Configuration

For production deployment:

```env
REACT_APP_API_URL=https://your-api-domain.com
REACT_APP_WS_URL=wss://your-api-domain.com/ws
REACT_APP_ENV=production
REACT_APP_DEBUG=false
```

### Static Hosting

The built app can be deployed to:
- Netlify, Vercel, or similar static hosts
- Nginx or Apache web servers
- AWS S3 + CloudFront
- Docker containers

## Browser Support

- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

## Performance

- Code splitting for optimal loading
- Lazy loading of components
- WebSocket connection management
- Optimized re-renders with React.memo
- Image and asset optimization

## Contributing

1. Follow TypeScript and React best practices
2. Write tests for new components and features
3. Ensure responsive design works on all devices
4. Test WebSocket connections thoroughly
5. Update documentation for new features

## Troubleshooting

### Common Issues

**API Connection Failed**
- Check if backend is running on correct port
- Verify CORS configuration
- Check network connectivity

**WebSocket Connection Issues**
- Ensure WebSocket endpoint is accessible
- Check firewall and proxy settings
- Verify SSL/TLS configuration for production

**Build Errors**
- Clear node_modules and reinstall: `rm -rf node_modules package-lock.json && npm install`
- Check TypeScript compilation errors
- Verify all dependencies are compatible

### Development Tips

- Use React Developer Tools for debugging
- Enable debug mode in `.env` for verbose logging
- Monitor network tab for API request issues
- Use browser WebSocket inspector for real-time debugging
