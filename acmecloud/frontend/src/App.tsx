import React, { useState, useEffect, useCallback } from 'react';
import {
  ShoppingBag,
  Cpu,
  Server,
  Monitor,
  Shield,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Terminal,
  ExternalLink,
  X,
  Plus,
  Minus,
  Trash2,
  HardDrive,
  Activity,
  Layers,
  Zap,
} from 'lucide-react';

interface Product {
  id: string;
  name: string;
  category: string;
  price: number;
  specs: string[];
  description: string;
  badge?: string;
}

interface CartItem {
  product: Product;
  quantity: number;
}

interface BuildMeta {
  version: string;
  title: string;
  description: string;
  fault_type: string;
  expected_error_rate: number;
  expected_latency_p95: number;
  is_active?: boolean;
}

interface SystemStatus {
  service: string;
  current_version: string;
  is_healthy: boolean;
  error_rate: number;
  latency_p95_ms: number;
  requests_per_sec: number;
  db_pool_active: number;
  db_pool_max: number;
  traffic_running: boolean;
}

const PRODUCTS: Product[] = [
  {
    id: 'prod-tpu-matrix',
    name: 'Acme Matrix TPU Edge Box',
    category: 'Neural Accelerators',
    price: 2499.0,
    specs: ['128GB HBM3', '800 TFLOPS FP16', 'PCIe 5.0 x16', 'Passive Cooled'],
    description: 'High-density tensor processor unit tailored for on-premise inference and fine-tuning.',
    badge: 'Popular',
  },
  {
    id: 'prod-titan-edge',
    name: 'Titan Edge Node X86',
    category: 'Edge Infrastructure',
    price: 1299.0,
    specs: ['64 Core AMD EPYC', '128GB ECC DDR5', 'Dual 25GbE SFP28', 'IP67 Enclosure'],
    description: 'Ruggedized edge compute node with redundant power and telemetry sensors.',
  },
  {
    id: 'prod-horizon-6k',
    name: 'Horizon 6K Studio Display',
    category: 'Displays & Hardware',
    price: 899.0,
    specs: ['32-inch IPS Black', '6016 x 3384 Resolution', '120Hz Refresh', '1000 nits Peak HDR'],
    description: 'Color-calibrated reference display with integrated Thunderbolt 4 KVM dock.',
  },
  {
    id: 'prod-aegis-gateway',
    name: 'Aegis Telemetry Gateway',
    category: 'Observability & SRE',
    price: 499.0,
    specs: ['eBPF Packet Engine', 'Zero-overhead Tap', '10Gbps Wire Speed', 'Hardware Tracing'],
    description: 'In-line hardware telemetry collector that hooks into autonomous incident detection engines.',
    badge: 'SRE Choice',
  },
  {
    id: 'prod-cluster-devbox',
    name: 'HyperCluster Workstation',
    category: 'Developer Workstations',
    price: 3499.0,
    specs: ['96 Core Threadripper', '256GB Unified RAM', 'Liquid Cooled', 'Whisper Quiet < 22dB'],
    description: 'The definitive local compilation and simulation rig for systems engineering teams.',
  },
  {
    id: 'prod-qsfp-module',
    name: 'UltraFiber 800G QSFP-DD',
    category: 'High-Speed Interconnect',
    price: 249.0,
    specs: ['800Gbps Aggregate', 'Low Insertion Loss', 'Class 1 Laser', 'Hot Pluggable'],
    description: 'Carrier-grade optical interconnect module for low-jitter spine-and-leaf fabrics.',
  },
];

export default function App() {
  const [cart, setCart] = useState<CartItem[]>([
    { product: PRODUCTS[0], quantity: 1 },
    { product: PRODUCTS[3], quantity: 2 },
  ]);
  const [isCartOpen, setIsCartOpen] = useState(false);
  const [isDevOpsOpen, setIsDevOpsOpen] = useState(false);
  const [activeCategory, setActiveCategory] = useState<string>('All');

  // Checkout flow state
  const [isCheckingOut, setIsCheckingOut] = useState(false);
  const [checkoutError, setCheckoutError] = useState<{ status: number; message: string; details?: string } | null>(null);
  const [confirmedOrder, setConfirmedOrder] = useState<{ orderId: string; total: number; latency: number } | null>(null);

  // DevOps & Chaos Lab state
  const [builds, setBuilds] = useState<BuildMeta[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [isDeploying, setIsDeploying] = useState(false);
  const [deployFeedback, setDeployFeedback] = useState<string | null>(null);

  // Poll system status and builds catalog
  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/acmecloud/status');
      if (res.ok) {
        const data = await res.json();
        setSystemStatus(data);
      }
    } catch {
      // Backend might be offline
    }
  }, []);

  const fetchBuilds = useCallback(async () => {
    try {
      const res = await fetch('/api/acmecloud/builds');
      if (res.ok) {
        const data = await res.json();
        setBuilds(data.builds || []);
      }
    } catch {
      // Backend might be offline
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    fetchBuilds();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, [fetchStatus, fetchBuilds]);

  // Cart operations
  const addToCart = (product: Product) => {
    setCart((prev) => {
      const existing = prev.find((item) => item.product.id === product.id);
      if (existing) {
        return prev.map((item) =>
          item.product.id === product.id ? { ...item, quantity: item.quantity + 1 } : item
        );
      }
      return [...prev, { product, quantity: 1 }];
    });
    setIsCartOpen(true);
  };

  const updateQuantity = (productId: string, delta: number) => {
    setCart((prev) =>
      prev
        .map((item) => {
          if (item.product.id === productId) {
            const newQty = item.quantity + delta;
            return newQty > 0 ? { ...item, quantity: newQty } : null;
          }
          return item;
        })
        .filter(Boolean) as CartItem[]
    );
  };

  const removeFromCart = (productId: string) => {
    setCart((prev) => prev.filter((item) => item.product.id !== productId));
  };

  const subtotal = cart.reduce((acc, item) => acc + item.product.price * item.quantity, 0);
  const tax = subtotal * 0.0825;
  const total = subtotal + tax;
  const totalItemCount = cart.reduce((acc, item) => acc + item.quantity, 0);

  // Real checkout against checkout-service
  const handleCheckout = async () => {
    if (cart.length === 0) return;
    setIsCheckingOut(true);
    setCheckoutError(null);
    const startTime = performance.now();

    try {
      const response = await fetch('/checkout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          customer_id: '00000000-0000-0000-0000-000000000001',
          total_amount: total.toFixed(2),
          currency: 'USD',
        }),
      });

      const elapsed = Math.round(performance.now() - startTime);

      if (response.ok) {
        const data = await response.json();
        setConfirmedOrder({
          orderId: data.order_id || 'ORD-' + Math.random().toString(36).substring(2, 9).toUpperCase(),
          total: total,
          latency: elapsed,
        });
        setCart([]);
        setIsCartOpen(false);
      } else {
        const errorText = await response.text();
        let parsedDetail = errorText;
        try {
          const jsonErr = JSON.parse(errorText);
          parsedDetail = jsonErr.detail || jsonErr.message || errorText;
        } catch {
          // Keep raw text
        }

        setCheckoutError({
          status: response.status,
          message:
            response.status === 500
              ? 'Checkout Service Internal Server Error'
              : response.status === 502 || response.status === 504
              ? 'Gateway Upstream Failure'
              : 'Transaction Declined',
          details: parsedDetail || 'Connection to transaction pool exhausted.',
        });
      }
    } catch (err: any) {
      setCheckoutError({
        status: 503,
        message: 'Checkout Service Unreachable',
        details: err?.message || 'Unable to connect to http://localhost:8001/checkout.',
      });
    } finally {
      setIsCheckingOut(false);
      fetchStatus();
    }
  };

  // Deploy build via AcmeCloud API
  const handleDeploy = async (version: string) => {
    setIsDeploying(true);
    setDeployFeedback(`Deploying build v${version}...`);
    try {
      const res = await fetch('/api/acmecloud/deploy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ service: 'checkout-service', version }),
      });
      if (res.ok) {
        const data = await res.json();
        setDeployFeedback(`Build v${version} deployed. Service reloaded.`);
        await fetchStatus();
        await fetchBuilds();
      } else {
        setDeployFeedback(`Failed to deploy build v${version}.`);
      }
    } catch {
      setDeployFeedback('Network error while deploying build.');
    } finally {
      setIsDeploying(false);
      setTimeout(() => setDeployFeedback(null), 4000);
    }
  };

  // Toggle continuous load traffic
  const handleToggleTraffic = async () => {
    try {
      const res = await fetch('/api/acmecloud/traffic/toggle', { method: 'POST' });
      if (res.ok) {
        await fetchStatus();
      }
    } catch {
      // Backend offline
    }
  };

  const categories = ['All', 'Neural Accelerators', 'Edge Infrastructure', 'Displays & Hardware', 'Observability & SRE', 'Developer Workstations'];
  const filteredProducts = activeCategory === 'All' ? PRODUCTS : PRODUCTS.filter((p) => p.category === activeCategory);

  return (
    <div className="min-h-screen bg-[#090a0f] text-slate-100 flex flex-col font-sans selection:bg-cyan-500/20 selection:text-cyan-300">
      {/* Top Notification / System Bar */}
      <div className="border-b border-[#1b2030] bg-[#0c0e15] px-4 py-2 text-xs flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 font-mono">
            <span
              className={`w-2 h-2 rounded-full ${
                systemStatus?.is_healthy ? 'bg-emerald-400 animate-pulse-subtle' : 'bg-red-500 animate-ping'
              }`}
            />
            <span className="text-slate-400 font-medium">Checkout Service:</span>
            <span className="text-slate-200">{systemStatus?.current_version ? `v${systemStatus.current_version}` : 'v2.4.0'}</span>
            <span
              className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase ${
                systemStatus?.is_healthy
                  ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/60'
                  : 'bg-red-950 text-red-400 border border-red-800/60'
              }`}
            >
              {systemStatus?.is_healthy ? 'Nominal' : 'Incident Active'}
            </span>
          </div>
          {systemStatus && (
            <div className="hidden md:flex items-center gap-4 text-slate-500 font-mono">
              <span>Err: {(systemStatus.error_rate * 100).toFixed(1)}%</span>
              <span>P95: {systemStatus.latency_p95_ms.toFixed(0)}ms</span>
              <span>Pool: {systemStatus.db_pool_active}/{systemStatus.db_pool_max}</span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsDevOpsOpen(true)}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#181c2b] hover:bg-[#20263a] border border-[#2b334c] text-cyan-400 font-mono transition-colors"
          >
            <Terminal className="w-3.5 h-3.5" />
            <span>DevOps &amp; Chaos Lab</span>
          </button>
          <a
            href="http://localhost:3000"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-slate-400 hover:text-slate-200 transition-colors"
          >
            <span>Aegis SRE Mission Control</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>

      {/* Main Store Header */}
      <header className="sticky top-0 z-30 border-b border-[#181d2a] bg-[#090a0f]/90 backdrop-blur-md px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-3 cursor-pointer">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-600 to-blue-500 flex items-center justify-center font-bold text-white shadow-lg shadow-cyan-500/20 font-mono">
                A
              </div>
              <div>
                <span className="text-base font-bold tracking-tight text-white block leading-none">ACME SYSTEMS</span>
                <span className="text-[10px] text-slate-400 font-mono uppercase tracking-wider">Enterprise Developer Hardware</span>
              </div>
            </div>

            <nav className="hidden lg:flex items-center gap-6 text-sm text-slate-300">
              <button
                onClick={() => setActiveCategory('All')}
                className={`transition-colors ${activeCategory === 'All' ? 'text-cyan-400 font-medium' : 'hover:text-white'}`}
              >
                Catalog
              </button>
              <button
                onClick={() => setActiveCategory('Neural Accelerators')}
                className={`transition-colors ${activeCategory === 'Neural Accelerators' ? 'text-cyan-400 font-medium' : 'hover:text-white'}`}
              >
                Neural Accelerators
              </button>
              <button
                onClick={() => setActiveCategory('Edge Infrastructure')}
                className={`transition-colors ${activeCategory === 'Edge Infrastructure' ? 'text-cyan-400 font-medium' : 'hover:text-white'}`}
              >
                Edge Nodes
              </button>
              <button
                onClick={() => setActiveCategory('Displays & Hardware')}
                className={`transition-colors ${activeCategory === 'Displays & Hardware' ? 'text-cyan-400 font-medium' : 'hover:text-white'}`}
              >
                Displays
              </button>
            </nav>
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={() => setIsCartOpen(true)}
              className="relative flex items-center gap-2.5 px-4 py-2 rounded-lg bg-[#141824] hover:bg-[#1c2233] border border-[#242c42] text-white text-sm font-medium transition-all"
            >
              <ShoppingBag className="w-4 h-4 text-cyan-400" />
              <span>Cart</span>
              {totalItemCount > 0 && (
                <span className="px-1.5 py-0.5 rounded-full bg-cyan-500 text-black text-xs font-mono font-bold leading-none">
                  {totalItemCount}
                </span>
              )}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-8">
        {/* Confirmed Order Banner */}
        {confirmedOrder && (
          <div className="mb-8 p-6 rounded-xl bg-[#0e1c18] border border-emerald-500/40 text-emerald-200 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-full bg-emerald-500/20 flex items-center justify-center shrink-0">
                <CheckCircle2 className="w-6 h-6 text-emerald-400" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Order Confirmed</h3>
                <p className="text-xs text-emerald-300/80 font-mono mt-0.5">
                  Order ID: {confirmedOrder.orderId} · Total: ${confirmedOrder.total.toFixed(2)} USD · Latency: {confirmedOrder.latency}ms
                </p>
                <p className="text-xs text-slate-300 mt-1">
                  Persisted to AcmeCloud PostgreSQL orders ledger. Transaction verified via checkout-service.
                </p>
              </div>
            </div>
            <button
              onClick={() => setConfirmedOrder(null)}
              className="px-4 py-2 rounded bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 text-xs font-semibold uppercase tracking-wider transition-colors"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Checkout Failure Banner with Direct Aegis Link */}
        {checkoutError && (
          <div className="mb-8 p-6 rounded-xl bg-[#200e12] border border-red-500/50 text-red-200">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-full bg-red-500/20 flex items-center justify-center shrink-0 mt-0.5">
                  <AlertTriangle className="w-6 h-6 text-red-400" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded bg-red-950 text-red-400 border border-red-800 text-[11px] font-mono font-bold">
                      HTTP {checkoutError.status}
                    </span>
                    <h3 className="text-lg font-bold text-white">{checkoutError.message}</h3>
                  </div>
                  <p className="text-xs font-mono text-red-300/90 mt-1">
                    {checkoutError.details}
                  </p>
                  <p className="text-xs text-slate-400 mt-2">
                    The checkout-service failed to process the transaction. Customer checkouts are currently dropping.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                <a
                  href="http://localhost:3000"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-red-500 hover:bg-red-600 text-white text-xs font-bold uppercase tracking-wider transition-all shadow-lg shadow-red-500/20"
                >
                  <span>Resolve in Aegis Copilot</span>
                  <ExternalLink className="w-4 h-4" />
                </a>
                <button
                  onClick={() => setCheckoutError(null)}
                  className="px-3 py-2 rounded bg-white/5 hover:bg-white/10 text-slate-300 text-xs transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Hero Section */}
        <section className="mb-12 rounded-2xl border border-[#1b2234] bg-gradient-to-b from-[#111422] to-[#0b0d14] p-8 md:p-12 relative overflow-hidden">
          <div className="absolute right-0 top-0 bottom-0 w-1/2 pointer-events-none opacity-10 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-cyan-400 via-transparent to-transparent" />
          
          <div className="relative max-w-2xl">
            <span className="inline-block px-3 py-1 rounded-full bg-cyan-950/80 border border-cyan-800/60 text-cyan-400 font-mono text-xs uppercase tracking-wider font-semibold mb-4">
              Direct-to-Engineer Fulfillment
            </span>
            <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight text-white mb-4 leading-tight">
              Hardware Crafted for Autonomous Compute.
            </h1>
            <p className="text-base text-slate-300 leading-relaxed mb-6">
              Low-latency edge nodes, tensor acceleration units, and engineering reference hardware backed by AcmeCloud high-availability architecture.
            </p>
            <div className="flex flex-wrap items-center gap-4">
              <button
                onClick={() => {
                  const el = document.getElementById('catalog-grid');
                  el?.scrollIntoView({ behavior: 'smooth' });
                }}
                className="flex items-center gap-2 px-5 py-3 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-black font-semibold text-sm transition-all shadow-lg shadow-cyan-500/25"
              >
                <span>Browse Architecture</span>
                <ArrowRight className="w-4 h-4" />
              </button>
              <button
                onClick={() => setIsDevOpsOpen(true)}
                className="flex items-center gap-2 px-5 py-3 rounded-lg bg-[#181d2c] hover:bg-[#22293e] border border-[#2b3550] text-slate-200 text-sm font-medium transition-all"
              >
                <Terminal className="w-4 h-4 text-cyan-400" />
                <span>Simulate Builds &amp; Chaos</span>
              </button>
            </div>
          </div>
        </section>

        {/* Category Filter Pills */}
        <div className="flex items-center gap-2 overflow-x-auto pb-4 mb-8">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`px-4 py-2 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
                activeCategory === cat
                  ? 'bg-cyan-500 text-black font-semibold shadow-md shadow-cyan-500/20'
                  : 'bg-[#121520] hover:bg-[#1a1f30] text-slate-300 border border-[#1e2436]'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Product Grid */}
        <div id="catalog-grid" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredProducts.map((product) => (
            <div
              key={product.id}
              className="rounded-xl border border-[#1a2030] bg-[#0e111a] hover:border-[#28324c] transition-all flex flex-col justify-between overflow-hidden group"
            >
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-[11px] font-mono text-cyan-400 uppercase tracking-wider">
                    {product.category}
                  </span>
                  {product.badge && (
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase bg-cyan-950 text-cyan-300 border border-cyan-800">
                      {product.badge}
                    </span>
                  )}
                </div>

                {/* Abstract Hardware Illustration */}
                <div className="w-full h-36 rounded-lg bg-[#090b12] border border-[#171c2a] mb-5 flex items-center justify-center relative overflow-hidden group-hover:border-cyan-500/30 transition-colors">
                  <div className="absolute inset-0 bg-[radial-gradient(#1f293d_1px,transparent_1px)] [background-size:12px_12px] opacity-40" />
                  {product.category.includes('Accelerator') && <Cpu className="w-12 h-12 text-cyan-400/80" />}
                  {product.category.includes('Infrastructure') && <Server className="w-12 h-12 text-blue-400/80" />}
                  {product.category.includes('Displays') && <Monitor className="w-12 h-12 text-cyan-300/80" />}
                  {product.category.includes('Observability') && <Shield className="w-12 h-12 text-emerald-400/80" />}
                  {product.category.includes('Workstations') && <Layers className="w-12 h-12 text-indigo-400/80" />}
                  {product.category.includes('Interconnect') && <Zap className="w-12 h-12 text-amber-400/80" />}
                </div>

                <h3 className="text-lg font-bold text-white mb-2 group-hover:text-cyan-300 transition-colors">
                  {product.name}
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed mb-4">
                  {product.description}
                </p>

                {/* Specs Pills */}
                <div className="flex flex-wrap gap-1.5 mb-6">
                  {product.specs.map((spec, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 rounded bg-[#151926] text-slate-300 text-[10px] font-mono border border-[#20273c]"
                    >
                      {spec}
                    </span>
                  ))}
                </div>
              </div>

              <div className="p-6 pt-0 border-t border-[#161a28] flex items-center justify-between mt-auto bg-[#0a0c14]/50">
                <div>
                  <span className="text-[10px] text-slate-500 font-mono block">UNIT PRICE</span>
                  <span className="text-xl font-bold font-mono text-white">
                    ${product.price.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                  </span>
                </div>
                <button
                  onClick={() => addToCart(product)}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-black text-xs font-bold uppercase tracking-wider transition-all"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add to Cart</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      </main>

      {/* Cart Drawer */}
      {isCartOpen && (
        <div className="fixed inset-0 z-50 overflow-hidden">
          <div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm transition-opacity"
            onClick={() => setIsCartOpen(false)}
          />

          <div className="absolute inset-y-0 right-0 max-w-full flex pl-10">
            <div className="w-screen max-w-md bg-[#0d0f17] border-l border-[#1d2334] text-slate-100 flex flex-col shadow-2xl">
              {/* Drawer Header */}
              <div className="px-6 py-5 border-b border-[#1b2132] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShoppingBag className="w-5 h-5 text-cyan-400" />
                  <h2 className="text-base font-bold text-white">Your Order</h2>
                  <span className="px-2 py-0.5 rounded-full bg-[#171c2b] text-cyan-400 text-xs font-mono">
                    {totalItemCount} items
                  </span>
                </div>
                <button
                  onClick={() => setIsCartOpen(false)}
                  className="p-1 rounded-lg hover:bg-[#1a1f30] text-slate-400 hover:text-white transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Items List */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {cart.length === 0 ? (
                  <div className="h-64 flex flex-col items-center justify-center text-center text-slate-500">
                    <ShoppingBag className="w-12 h-12 mb-3 stroke-[1.2]" />
                    <p className="text-sm font-medium text-slate-400">Your cart is empty</p>
                    <p className="text-xs text-slate-600 mt-1">Select developer hardware from the catalog to test checkout.</p>
                  </div>
                ) : (
                  cart.map((item) => (
                    <div
                      key={item.product.id}
                      className="p-4 rounded-lg bg-[#111420] border border-[#1b2234] flex items-center justify-between gap-4"
                    >
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm font-semibold text-white truncate">{item.product.name}</h4>
                        <span className="text-xs text-slate-400 font-mono">
                          ${item.product.price.toFixed(2)} each
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => updateQuantity(item.product.id, -1)}
                          className="w-7 h-7 rounded bg-[#181d2c] hover:bg-[#22293e] border border-[#2b354f] flex items-center justify-center text-slate-300 transition-colors"
                        >
                          <Minus className="w-3.5 h-3.5" />
                        </button>
                        <span className="w-6 text-center text-sm font-mono font-bold text-white">
                          {item.quantity}
                        </span>
                        <button
                          onClick={() => updateQuantity(item.product.id, 1)}
                          className="w-7 h-7 rounded bg-[#181d2c] hover:bg-[#22293e] border border-[#2b354f] flex items-center justify-center text-slate-300 transition-colors"
                        >
                          <Plus className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => removeFromCart(item.product.id)}
                          className="ml-2 text-slate-500 hover:text-red-400 transition-colors p-1"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* Drawer Footer with Checkout Button */}
              {cart.length > 0 && (
                <div className="p-6 border-t border-[#1b2132] bg-[#0a0c14] space-y-4">
                  <div className="space-y-1.5 text-xs text-slate-400">
                    <div className="flex justify-between">
                      <span>Subtotal</span>
                      <span className="font-mono text-slate-200">${subtotal.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Estimated Tax (8.25%)</span>
                      <span className="font-mono text-slate-200">${tax.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Fulfillment &amp; Express Delivery</span>
                      <span className="font-mono text-emerald-400">FREE</span>
                    </div>
                    <div className="pt-2 border-t border-[#1a1f30] flex justify-between text-sm font-bold text-white">
                      <span>Total Due</span>
                      <span className="font-mono text-cyan-400">${total.toFixed(2)} USD</span>
                    </div>
                  </div>

                  <div className="p-3 rounded bg-[#121624] border border-[#1e2538] text-[11px] text-slate-400">
                    <span className="font-mono text-slate-300 block mb-0.5">ENDPOINT TARGET:</span>
                    <span className="font-mono text-cyan-400">POST http://localhost:8001/checkout</span>
                  </div>

                  <button
                    onClick={handleCheckout}
                    disabled={isCheckingOut}
                    className="w-full py-3.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 disabled:bg-cyan-900 disabled:text-cyan-600 text-black font-bold text-sm uppercase tracking-wider flex items-center justify-center gap-2 transition-all shadow-lg shadow-cyan-500/20"
                  >
                    {isCheckingOut ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        <span>Sending to Checkout Service...</span>
                      </>
                    ) : (
                      <>
                        <span>Place Order · ${total.toFixed(2)}</span>
                        <ArrowRight className="w-4 h-4" />
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* DevOps & Chaos Lab Drawer */}
      {isDevOpsOpen && (
        <div className="fixed inset-0 z-50 overflow-hidden">
          <div
            className="absolute inset-0 bg-black/75 backdrop-blur-sm transition-opacity"
            onClick={() => setIsDevOpsOpen(false)}
          />

          <div className="absolute inset-y-0 right-0 max-w-full flex pl-10">
            <div className="w-screen max-w-lg bg-[#0b0d14] border-l border-[#1e2538] text-slate-100 flex flex-col shadow-2xl">
              {/* Header */}
              <div className="px-6 py-5 border-b border-[#1b2234] flex items-center justify-between bg-[#0e111a]">
                <div className="flex items-center gap-2.5">
                  <Terminal className="w-5 h-5 text-cyan-400" />
                  <div>
                    <h2 className="text-base font-bold text-white">DevOps &amp; Chaos Lab</h2>
                    <p className="text-[11px] text-slate-400 font-mono">AcmeCloud Target Environment Simulator</p>
                  </div>
                </div>
                <button
                  onClick={() => setIsDevOpsOpen(false)}
                  className="p-1 rounded-lg hover:bg-[#1a1f30] text-slate-400 hover:text-white transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Feedback toast */}
              {deployFeedback && (
                <div className="px-6 py-3 bg-cyan-950/80 border-b border-cyan-800 text-cyan-200 text-xs font-mono flex items-center gap-2">
                  <Activity className="w-4 h-4 text-cyan-400 animate-spin" />
                  <span>{deployFeedback}</span>
                </div>
              )}

              {/* Lab Content */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {/* Live Service Telemetry Card */}
                <div className="p-5 rounded-xl bg-[#111522] border border-[#1f273d]">
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">Live Service Status</span>
                    <button
                      onClick={fetchStatus}
                      className="p-1 rounded hover:bg-[#1b2132] text-slate-400 hover:text-slate-200 transition-colors"
                      title="Refresh Telemetry"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <div className="grid grid-cols-2 gap-4 font-mono text-xs mb-4">
                    <div className="p-3 rounded-lg bg-[#0c0e17] border border-[#192032]">
                      <span className="text-[10px] text-slate-500 block">CURRENT VERSION</span>
                      <span className="text-sm font-bold text-white">
                        {systemStatus?.current_version ? `v${systemStatus.current_version}` : 'v2.4.0'}
                      </span>
                    </div>
                    <div className="p-3 rounded-lg bg-[#0c0e17] border border-[#192032]">
                      <span className="text-[10px] text-slate-500 block">HEALTH STATE</span>
                      <span
                        className={`text-sm font-bold ${
                          systemStatus?.is_healthy ? 'text-emerald-400' : 'text-red-400'
                        }`}
                      >
                        {systemStatus?.is_healthy ? '200 OK (Nominal)' : 'CRITICAL (5xx Errors)'}
                      </span>
                    </div>
                    <div className="p-3 rounded-lg bg-[#0c0e17] border border-[#192032]">
                      <span className="text-[10px] text-slate-500 block">ERROR RATE</span>
                      <span className="text-sm font-bold text-white">
                        {systemStatus ? `${(systemStatus.error_rate * 100).toFixed(1)}%` : '0.0%'}
                      </span>
                    </div>
                    <div className="p-3 rounded-lg bg-[#0c0e17] border border-[#192032]">
                      <span className="text-[10px] text-slate-500 block">P95 LATENCY</span>
                      <span className="text-sm font-bold text-white">
                        {systemStatus ? `${systemStatus.latency_p95_ms.toFixed(0)} ms` : '42 ms'}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-3 border-t border-[#1b2132] text-xs">
                    <span className="text-slate-400">Background Traffic Generator:</span>
                    <button
                      onClick={handleToggleTraffic}
                      className={`px-3 py-1 rounded text-xs font-mono font-semibold transition-all ${
                        systemStatus?.traffic_running
                          ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                          : 'bg-[#181d2a] text-slate-400 border border-[#273046]'
                      }`}
                    >
                      {systemStatus?.traffic_running ? 'Running (Active)' : 'Stopped (Paused)'}
                    </button>
                  </div>
                </div>

                {/* Available Builds Catalog */}
                <div>
                  <h3 className="text-sm font-bold text-white mb-2 flex items-center justify-between">
                    <span>Deploy Operational Builds</span>
                    <span className="text-[11px] font-mono text-slate-400">checkout-service</span>
                  </h3>
                  <p className="text-xs text-slate-400 mb-4">
                    Inject specific builds to simulate operational incidents. Once injected, try checking out on the store or observe Aegis diagnosing the failure.
                  </p>

                  <div className="space-y-3">
                    {builds.length === 0 ? (
                      <div className="text-xs text-slate-500 font-mono">Loading available builds...</div>
                    ) : (
                      builds.map((b) => {
                        const isActive = b.version === systemStatus?.current_version;
                        const isBaseline = b.version === '2.4.0';

                        return (
                          <div
                            key={b.version}
                            className={`p-4 rounded-xl border transition-all ${
                              isActive
                                ? 'bg-[#0f1722] border-cyan-500/50 shadow-md shadow-cyan-500/10'
                                : 'bg-[#0e111a] border-[#1c2336] hover:border-[#2b3652]'
                            }`}
                          >
                            <div className="flex items-start justify-between gap-3 mb-2">
                              <div>
                                <div className="flex items-center gap-2">
                                  <span className="font-mono font-bold text-sm text-white">v{b.version}</span>
                                  <span
                                    className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold uppercase ${
                                      isBaseline
                                        ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                                        : 'bg-red-950 text-red-300 border border-red-800'
                                    }`}
                                  >
                                    {b.fault_type}
                                  </span>
                                  {isActive && (
                                    <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-cyan-500 text-black">
                                      Active
                                    </span>
                                  )}
                                </div>
                                <h4 className="text-xs font-semibold text-slate-200 mt-1">{b.title}</h4>
                              </div>

                              <button
                                onClick={() => handleDeploy(b.version)}
                                disabled={isDeploying || isActive}
                                className={`px-3 py-1.5 rounded text-xs font-bold font-mono uppercase tracking-wider transition-all ${
                                  isActive
                                    ? 'bg-[#181d2a] text-slate-500 cursor-not-allowed border border-[#23293c]'
                                    : isBaseline
                                    ? 'bg-emerald-600 hover:bg-emerald-500 text-white'
                                    : 'bg-red-600 hover:bg-red-500 text-white'
                                }`}
                              >
                                {isActive ? 'Live' : isDeploying ? 'Deploying...' : 'Deploy'}
                              </button>
                            </div>

                            <p className="text-xs text-slate-400 mb-2 leading-relaxed">
                              {b.description}
                            </p>

                            <div className="flex items-center gap-4 text-[10px] font-mono text-slate-500 pt-2 border-t border-[#181d2b]">
                              <span>Expected Error: {(b.expected_error_rate * 100).toFixed(0)}%</span>
                              <span>Target Latency: {b.expected_latency_p95}ms</span>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>

                {/* External Links */}
                <div className="p-4 rounded-xl bg-[#0e111a] border border-[#1b2234] space-y-2">
                  <span className="text-xs font-mono text-slate-400 uppercase tracking-wider block mb-2">Connected Surfaces</span>
                  <a
                    href="http://localhost:3000"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-between p-2.5 rounded-lg bg-[#131622] hover:bg-[#1a1f30] text-xs text-slate-200 transition-colors"
                  >
                    <span>Aegis SRE Mission Control</span>
                    <ExternalLink className="w-3.5 h-3.5 text-cyan-400" />
                  </a>
                  <a
                    href="http://localhost:3001"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-between p-2.5 rounded-lg bg-[#131622] hover:bg-[#1a1f30] text-xs text-slate-200 transition-colors"
                  >
                    <span>Grafana Observability Dashboards</span>
                    <ExternalLink className="w-3.5 h-3.5 text-cyan-400" />
                  </a>
                  <a
                    href="http://localhost:9090"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-between p-2.5 rounded-lg bg-[#131622] hover:bg-[#1a1f30] text-xs text-slate-200 transition-colors"
                  >
                    <span>Prometheus TSDB</span>
                    <ExternalLink className="w-3.5 h-3.5 text-cyan-400" />
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
