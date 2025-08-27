import React, { useState, useEffect, useCallback } from 'react';
import './App.css';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Badge } from './components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './components/ui/table';
import { Alert, AlertDescription, AlertTitle } from './components/ui/alert';
import { Separator } from './components/ui/separator';
import { 
  Shield, 
  Activity, 
  AlertTriangle, 
  Wifi, 
  WifiOff, 
  Eye, 
  Globe, 
  Smartphone, 
  Users,
  TrendingUp,
  Clock,
  Play,
  Pause,
  RotateCcw
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const WS_URL = BACKEND_URL.replace('https://', 'wss://').replace('http://', 'ws://');

function App() {
  const [isConnected, setIsConnected] = useState(false);
  const [isListening, setIsListening] = useState(true);
  const [stats, setStats] = useState({
    totalFlows: 0,
    totalLeaks: 0,
    recentFlows: [],
    privacyLeaks: []
  });
  const [allFlows, setAllFlows] = useState([]);
  const [ws, setWs] = useState(null);
  const [connectionAttempts, setConnectionAttempts] = useState(0);
  const [lastUpdate, setLastUpdate] = useState(null);

  const connectWebSocket = useCallback(() => {
    if (!isListening) return;
    
    try {
      const websocketUrl = `${WS_URL}/ws/dashboard`;
      console.log('Attempting WebSocket connection to:', websocketUrl);
      
      const websocket = new WebSocket(websocketUrl);
      
      websocket.onopen = () => {
        console.log('Connected to Mobile Privacy Detector backend');
        setIsConnected(true);
        setConnectionAttempts(0);
      };
      
      websocket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          console.log('Received real-time data:', message);
          setLastUpdate(new Date());
          
          if (message.type === 'stats_update') {
            setStats(message.data);
            setAllFlows(message.data.recentFlows || []);
          } else if (message.type === 'new_traffic') {
            const newFlow = message.data;
            
            // Add new flow to the beginning of the list
            setAllFlows(prev => [newFlow, ...prev].slice(0, 100)); // Keep last 100
            
            // Update stats
            setStats(prev => ({
              ...prev,
              totalFlows: prev.totalFlows + 1,
              totalLeaks: newFlow.leakType ? prev.totalLeaks + 1 : prev.totalLeaks,
              privacyLeaks: newFlow.leakType 
                ? [newFlow, ...prev.privacyLeaks].slice(0, 50)
                : prev.privacyLeaks
            }));
            
            // Show notification for privacy leaks
            if (newFlow.leakType) {
              console.warn(`🚨 PRIVACY LEAK DETECTED: ${newFlow.leakType} - ${newFlow.leakDetail}`);
            }
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
      
      websocket.onclose = (event) => {
        console.log('WebSocket connection closed:', event.code, event.reason);
        setIsConnected(false);
        
        if (isListening && connectionAttempts < 5) {
          // Attempt to reconnect with backoff
          const delay = Math.min(1000 * Math.pow(2, connectionAttempts), 30000);
          console.log(`Reconnecting in ${delay/1000}s... (attempt ${connectionAttempts + 1}/5)`);
          setTimeout(() => {
            setConnectionAttempts(prev => prev + 1);
            connectWebSocket();
          }, delay);
        }
      };
      
      websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsConnected(false);
      };
      
      setWs(websocket);
    } catch (error) {
      console.error('Error connecting to WebSocket:', error);
      setIsConnected(false);
    }
  }, [isListening, connectionAttempts]);

  const toggleListening = () => {
    setIsListening(prev => {
      const newListening = !prev;
      if (!newListening && ws) {
        ws.close();
        setWs(null);
        setIsConnected(false);
      } else if (newListening) {
        setConnectionAttempts(0);
        connectWebSocket();
      }
      return newListening;
    });
  };

  const clearData = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/system/clear`, {
        method: 'POST',
      });
      if (response.ok) {
        setStats({ totalFlows: 0, totalLeaks: 0, recentFlows: [], privacyLeaks: [] });
        setAllFlows([]);
        console.log('Traffic data cleared');
      }
    } catch (error) {
      console.error('Error clearing data:', error);
    }
  };

  useEffect(() => {
    if (isListening) {
      connectWebSocket();
    }
    
    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [connectWebSocket, isListening]);

  const getLeakTypeColor = (leakType) => {
    switch (leakType) {
      case 'GPS_DATA': return 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900/20 dark:text-red-300 dark:border-red-800';
      case 'DEVICE_INFO': return 'bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/20 dark:text-orange-300 dark:border-orange-800';
      case 'PERSONAL_DATA': return 'bg-purple-100 text-purple-800 border-purple-200 dark:bg-purple-900/20 dark:text-purple-300 dark:border-purple-800';
      case 'TRACKING': return 'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/20 dark:text-yellow-300 dark:border-yellow-800';
      default: return 'bg-gray-100 text-gray-800 border-gray-200 dark:bg-gray-900/20 dark:text-gray-300 dark:border-gray-800';
    }
  };

  const getLeakTypeIcon = (leakType) => {
    switch (leakType) {
      case 'GPS_DATA': return <Globe className="w-4 h-4" />;
      case 'DEVICE_INFO': return <Smartphone className="w-4 h-4" />;
      case 'PERSONAL_DATA': return <Users className="w-4 h-4" />;
      case 'TRACKING': return <Eye className="w-4 h-4" />;
      default: return <AlertTriangle className="w-4 h-4" />;
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Shield className="w-8 h-8 text-emerald-400" />
              <div>
                <h1 className="text-2xl font-bold text-slate-100">Mobile Privacy Scanner</h1>
                <p className="text-sm text-slate-400">Real-time mobile network traffic analysis</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <button 
                onClick={toggleListening}
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg border transition-colors ${
                  isListening 
                    ? 'border-red-600 bg-red-600/10 text-red-400 hover:bg-red-600/20' 
                    : 'border-emerald-600 bg-emerald-600/10 text-emerald-400 hover:bg-emerald-600/20'
                }`}
              >
                {isListening ? (
                  <>
                    <Pause className="w-4 h-4" />
                    <span>Stop Monitoring</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" />
                    <span>Start Monitoring</span>
                  </>
                )}
              </button>

              <button 
                onClick={clearData}
                className="flex items-center space-x-2 px-4 py-2 rounded-lg border border-slate-600 bg-slate-800/50 text-slate-300 hover:bg-slate-800 transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
                <span>Clear Data</span>
              </button>
              
              <div className="flex items-center space-x-2">
                {isConnected ? (
                  <>
                    <Wifi className="w-4 h-4 text-emerald-400" />
                    <span className="text-sm font-medium text-emerald-400">
                      Connected{lastUpdate && ` • ${lastUpdate.toLocaleTimeString()}`}
                    </span>
                  </>
                ) : (
                  <>
                    <WifiOff className="w-4 h-4 text-red-400" />
                    <span className="text-sm font-medium text-red-400">
                      {isListening ? `Connecting...${connectionAttempts > 0 ? ` (${connectionAttempts}/5)` : ''}` : 'Not Monitoring'}
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-6 py-8">
        {!isConnected && isListening && (
          <Alert className="mb-6 bg-yellow-900/20 border-yellow-800">
            <AlertTriangle className="h-4 w-4 text-yellow-400" />
            <AlertTitle className="text-yellow-400">Waiting for Mobile Traffic</AlertTitle>
            <AlertDescription className="text-slate-300">
              Make sure your mobile device is connected and configured to use the proxy. 
              Start using apps on your phone to see traffic appear here.
            </AlertDescription>
          </Alert>
        )}

        <Tabs defaultValue="summary" className="space-y-6">
          <TabsList className="bg-slate-800 border-slate-700">
            <TabsTrigger value="summary" className="data-[state=active]:bg-slate-700">
              <TrendingUp className="w-4 h-4 mr-2" />
              Summary
            </TabsTrigger>
            <TabsTrigger value="traffic" className="data-[state=active]:bg-slate-700">
              <Activity className="w-4 h-4 mr-2" />
              Live Traffic Flows
            </TabsTrigger>
            <TabsTrigger value="alerts" className="data-[state=active]:bg-slate-700">
              <AlertTriangle className="w-4 h-4 mr-2" />
              Privacy Leak Alerts
            </TabsTrigger>
          </TabsList>

          {/* Summary Tab */}
          <TabsContent value="summary" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Card className="bg-slate-900/50 border-slate-700 backdrop-blur-sm">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg font-semibold text-slate-100 flex items-center">
                    <Activity className="w-5 h-5 mr-2 text-blue-400" />
                    Total Traffic Flows
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-blue-400">{stats.totalFlows}</div>
                  <p className="text-sm text-slate-400 mt-1">Network requests intercepted</p>
                </CardContent>
              </Card>

              <Card className="bg-slate-900/50 border-slate-700 backdrop-blur-sm">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg font-semibold text-slate-100 flex items-center">
                    <AlertTriangle className="w-5 h-5 mr-2 text-red-400" />
                    Privacy Leaks Detected
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-red-400">{stats.totalLeaks}</div>
                  <p className="text-sm text-slate-400 mt-1">Suspicious data transmissions</p>
                </CardContent>
              </Card>

              <Card className="bg-slate-900/50 border-slate-700 backdrop-blur-sm">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg font-semibold text-slate-100 flex items-center">
                    <Shield className="w-5 h-5 mr-2 text-emerald-400" />
                    Risk Level
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className={`text-3xl font-bold ${stats.totalLeaks > 10 ? 'text-red-400' : stats.totalLeaks > 5 ? 'text-yellow-400' : stats.totalLeaks > 0 ? 'text-orange-400' : 'text-emerald-400'}`}>
                    {stats.totalLeaks > 10 ? 'CRITICAL' : stats.totalLeaks > 5 ? 'HIGH' : stats.totalLeaks > 0 ? 'MEDIUM' : 'LOW'}
                  </div>
                  <p className="text-sm text-slate-400 mt-1">Current privacy threat level</p>
                </CardContent>
              </Card>
            </div>

            {/* Recent Activity */}
            <Card className="bg-slate-900/50 border-slate-700 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-lg font-semibold text-slate-100 flex items-center">
                  <Clock className="w-5 h-5 mr-2 text-slate-400" />
                  Live Traffic Stream
                </CardTitle>
                <CardDescription className="text-slate-400">
                  Real-time network requests from your mobile device
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {allFlows.slice(0, 8).map((flow) => (
                    <div key={flow.flowId} className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 border border-slate-700 animate-fade-in">
                      <div className="flex items-center space-x-3">
                        <Badge variant="outline" className="border-slate-600 text-slate-300 font-mono">
                          {flow.method}
                        </Badge>
                        <div>
                          <div className="text-sm font-medium text-slate-200">{flow.host}</div>
                          <div className="text-xs text-slate-400 font-mono max-w-xs truncate">{flow.url}</div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className="text-xs text-slate-500 font-mono">{flow.timestamp}</span>
                        {flow.leakType ? (
                          <Badge className={`${getLeakTypeColor(flow.leakType)} animate-pulse`}>
                            {getLeakTypeIcon(flow.leakType)}
                            <span className="ml-1">{flow.leakType}</span>
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="border-emerald-600 text-emerald-400 bg-emerald-950/20">
                            Safe
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))}
                  {allFlows.length === 0 && (
                    <div className="text-center py-12 text-slate-400">
                      <Activity className="w-16 h-16 mx-auto mb-4 text-slate-600" />
                      <h3 className="text-lg font-semibold text-slate-300 mb-2">Waiting for Mobile Traffic</h3>
                      <p>
                        Start using apps on your phone to see network requests appear here in real-time.
                      </p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Live Traffic Flows Tab */}
          <TabsContent value="traffic">
            <Card className="bg-slate-900/50 border-slate-700 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-lg font-semibold text-slate-100">Live Traffic Flows</CardTitle>
                <CardDescription className="text-slate-400">
                  Real-time stream of all network requests from your mobile device
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="rounded-lg border border-slate-700 bg-slate-800/30">
                  <Table>
                    <TableHeader>
                      <TableRow className="border-slate-700 hover:bg-slate-800/50">
                        <TableHead className="text-slate-300">Time</TableHead>
                        <TableHead className="text-slate-300">Method</TableHead>
                        <TableHead className="text-slate-300">Host</TableHead>
                        <TableHead className="text-slate-300">URL</TableHead>
                        <TableHead className="text-slate-300">Status</TableHead>
                        <TableHead className="text-slate-300">Privacy</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {allFlows.map((flow) => (
                        <TableRow key={flow.flowId} className="border-slate-700 hover:bg-slate-800/50">
                          <TableCell className="text-slate-400 font-mono text-sm">{flow.timestamp}</TableCell>
                          <TableCell>
                            <Badge variant="outline" className="border-slate-600 text-slate-300 font-mono">
                              {flow.method}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-slate-300 font-medium">{flow.host}</TableCell>
                          <TableCell className="text-slate-400 font-mono text-sm max-w-xs truncate">{flow.url}</TableCell>
                          <TableCell>
                            <Badge 
                              variant="outline" 
                              className={flow.status.startsWith('2') 
                                ? 'border-emerald-600 text-emerald-400' 
                                : flow.status.startsWith('4') || flow.status.startsWith('5')
                                ? 'border-red-600 text-red-400'
                                : 'border-slate-600 text-slate-300'
                              }
                            >
                              {flow.status}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {flow.leakType ? (
                              <Badge className={getLeakTypeColor(flow.leakType)}>
                                {getLeakTypeIcon(flow.leakType)}
                                <span className="ml-1">{flow.leakType}</span>
                              </Badge>
                            ) : (
                              <Badge variant="outline" className="border-emerald-600 text-emerald-400 bg-emerald-950/20">
                                Safe
                              </Badge>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  
                  {allFlows.length === 0 && (
                    <div className="text-center py-12 text-slate-400">
                      <Activity className="w-16 h-16 mx-auto mb-4 text-slate-600" />
                      <h3 className="text-lg font-semibold text-slate-300 mb-2">No Traffic Data</h3>
                      <p>Use apps on your mobile device to generate network traffic.</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Privacy Leak Alerts Tab */}
          <TabsContent value="alerts">
            <div className="space-y-4">
              {stats.privacyLeaks?.map((leak) => (
                <Alert key={leak.flowId} className="bg-slate-900/50 border-red-800 backdrop-blur-sm">
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0 mt-1">
                      {getLeakTypeIcon(leak.leakType)}
                    </div>
                    <div className="flex-1">
                      <AlertTitle className="text-red-400 font-semibold flex items-center space-x-2">
                        <span>{leak.leakType} Detected</span>
                        <Badge className={getLeakTypeColor(leak.leakType)}>
                          {leak.method}
                        </Badge>
                        <span className="text-xs text-slate-500 font-mono">{leak.timestamp}</span>
                      </AlertTitle>
                      <AlertDescription className="text-slate-300 mt-2">
                        <div className="space-y-2">
                          <p className="font-medium">{leak.leakDetail}</p>
                          <Separator className="bg-slate-700" />
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                            <div>
                              <span className="text-slate-400">Host:</span>
                              <span className="ml-2 font-mono text-slate-200">{leak.host}</span>
                            </div>
                            <div>
                              <span className="text-slate-400">URL:</span>
                              <span className="ml-2 font-mono text-slate-200 truncate block">{leak.url}</span>
                            </div>
                          </div>
                        </div>
                      </AlertDescription>
                    </div>
                  </div>
                </Alert>
              ))}
              
              {(!stats.privacyLeaks || stats.privacyLeaks.length === 0) && (
                <Card className="bg-slate-900/50 border-slate-700 backdrop-blur-sm">
                  <CardContent className="text-center py-12">
                    <Shield className="w-16 h-16 mx-auto text-emerald-400 mb-4" />
                    <h3 className="text-lg font-semibold text-slate-200 mb-2">No Privacy Leaks Detected</h3>
                    <p className="text-slate-400">
                      {stats.totalFlows > 0 
                        ? "All intercepted network traffic appears to be safe." 
                        : "Start using apps on your mobile device to monitor for privacy leaks."
                      }
                    </p>
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

export default App;