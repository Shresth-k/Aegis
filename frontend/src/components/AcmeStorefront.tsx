import React, { useState, useEffect } from 'react';
import {
  ShoppingBag,
  ShoppingCart,
  Server,
  Cpu,
  Layers,
  Activity,
  CheckCircle2,
  AlertTriangle,
  X,
  ChevronRight,
  Terminal,
  Sliders,
  RefreshCw,
  Play,
  Square,
  ArrowRight,
  ShieldCheck,
  HardDrive,
  Monitor,
  Zap,
  ExternalLink,
  Plus,
  Minus,
  Trash2
} from 'lucide-react';

interface Product {
  id: string;
  name: string;
  category: 'Compute & AI' | 'Storage Arrays' | 'Control Terminals';
  price: number;
  description: string;
  specs: string[];
  stockBadge: string;
  stockCount: number;
  iconType: 'cpu' | 'server' | 'storage' | 'display' | 'keydeck' | 'clock';
}

const PRODUCTS: Product[] = [
  {
    id: 'prod-001',
    name: 'Acme Neural Studio Pro 9000',
    category: 'Compute & AI',
    price: 4899,
    description: 'High-density desk-side neural accelerator designed for continuous local fine-tuning and inference pipelines.',
    specs: ['8x SXM5 Tensor Accelerators', '3.2 Tbps Quantum-2 InfiniBand', 'Liquid Cooled Thermal Loop', '1600W Titanium Redundant'],
    stockBadge: 'In Stock',
    stockCount: 14,
    iconType: 'cpu'
  },
  {
    id: 'prod-002',
    name: 'Acme Edge Gateway Server 2U',
    category: 'Compute & AI',
    price: 2899,
    description: 'Ruggedized rackmount compute chassis for distributed edge ingest and real-time streaming telemetry.',
    specs: ['Dual AMD EPYC 9654 (128 Cores)', '256GB ECC DDR5-4800', '4x 100GbE SFP28 Interfaces', 'Hardware TPM 2.0 Secure Boot'],
    stockBadge: 'In Stock',
    stockCount: 28,
    iconType: 'server'
  },
  {
    id: 'prod-003',
    name: 'Acme High-Density NVMe Vault 64TB',
    category: 'Storage Arrays',
    price: 3200,
    description: 'Low-latency NVMe PCIe Gen5 data store engineered for high-throughput time-series databases and event logs.',
    specs: ['64TB Raw NVMe Gen5 U.2', '14.5 GB/s Sequential Read', '3.8M Random Read IOPS', 'Hardware AES-256 SED'],
    stockBadge: 'In Stock',
    stockCount: 9,
    iconType: 'storage'
  },
  {
    id: 'prod-004',
    name: 'Acme Curved Studio Terminal OLED 49"',
    category: 'Control Terminals',
    price: 1299,
    description: 'Ultra-wide 32:9 dual QHD panoramic monitor calibrated for multi-pane SRE telemetry and live topology maps.',
    specs: ['5120 x 1440 Resolution (240Hz)', '0.03ms GtG Response Time', 'Dual DisplayPort 2.1 & USB-C 90W', 'Hardware KVM Switch Built-in'],
    stockBadge: 'Low Stock (4 left)',
    stockCount: 4,
    iconType: 'display'
  },
  {
    id: 'prod-005',
    name: 'Acme SRE Mechanical Keydeck MK-IV',
    category: 'Control Terminals',
    price: 389,
    description: 'Tactile mechanical switch deck featuring 12 programmable miniature OLED macro keys for instant runbook execution.',
    specs: ['Hot-swappable Box Navy Switches', '12 Dynamic Mini-OLED Keycaps', 'CNC Anodized Slate Chassis', 'Gasket Mounted Sound Dampening'],
    stockBadge: 'In Stock',
    stockCount: 42,
    iconType: 'keydeck'
  },
  {
    id: 'prod-006',
    name: 'Acme Ultra-Low Latency Precision Clock',
    category: 'Compute & AI',
    price: 1450,
    description: 'Precision atomic timing module enabling sub-microsecond distributed transaction synchronization and trace ordering.',
    specs: ['Rubidium Atomic Reference Standard', 'IEEE 1588v2 PTP Hardware Timestamping', 'Sub-nanosecond Allan Deviation', 'PCIe x4 Low-Profile Form Factor'],
    stockBadge: 'In Stock',
    stockCount: 17,
    iconType: 'clock'
  }
];

interface BuildInfo {
  version: string;
  name: string;
  scenario: string;
  status: 'STABLE' | 'DEGRADED';
  pool_max: number;
  expected_error_rate: string;
  symptoms: string[];
}

interface AcmeStatus {
  service: string;
  active_version: string;
  health: {
    status: string;
    version: string;
    traffic_rate_rps: number;
    error_rate_pct: number;
    p99_latency_ms: number;
    db_pool_utilization_pct: number;
  };
  traffic_running: boolean;
  total_builds_available: number;
}

interface CartItem {
  product: Product;
  quantity: number;
}

interface CheckoutResult {
  status: 'CONFIRMED' | 'FAILED';
  orderId?: string;
  version?: string;
  executionMode?: string;
  message?: string;
  warning?: string;
  errorCode?: number;
  errorDetail?: string;
}

interface AcmeStorefrontProps {
  onOpenAegis?: () => void;
}

export const AcmeStorefront: React.FC<AcmeStorefrontProps> = ({ onOpenAegis }) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('All Systems');
  const [cart, setCart] = useState<CartItem[]>([
    { product: PRODUCTS[1], quantity: 1 } // Acme Edge Gateway Server by default
  ]);
  const [isCartOpen, setIsCartOpen] = useState<boolean>(false);
  const [isDevDrawerOpen, setIsDevDrawerOpen] = useState<boolean>(false);
  const [isCheckingOut, setIsCheckingOut] = useState<boolean>(false);
  const [checkoutStep, setCheckoutStep] = useState<string>('');
  const [checkoutResult, setCheckoutResult] = useState<CheckoutResult | null>(null);

  // DevOps & Chaos state
  const [builds, setBuilds] = useState<BuildInfo[]>([]);
  const [acmeStatus, setAcmeStatus] = useState<AcmeStatus | null>(null);
  const [isDeployingBuild, setIsDeployingBuild] = useState<string | null>(null);
  const [isTogglingTraffic, setIsTogglingTraffic] = useState<boolean>(false);

  // Fetch status and builds
  const refreshStatus = async () => {
    try {
      const res = await fetch('/api/acmecloud/status');
      if (res.ok) {
        const data = await res.json();
        setAcmeStatus(data);
      }
    } catch (err) {
      console.warn('Failed to fetch AcmeCloud status:', err);
    }
  };

  const fetchBuilds = async () => {
    try {
      const res = await fetch('/api/acmecloud/builds');
      if (res.ok) {
        const data = await res.json();
        if (data.builds) setBuilds(data.builds);
      }
    } catch (err) {
      console.warn('Failed to fetch Acme builds:', err);
    }
  };

  useEffect(() => {
    refreshStatus();
    fetchBuilds();
    const interval = setInterval(refreshStatus, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleDeployBuild = async (version: string) => {
    setIsDeployingBuild(version);
    try {
      const res = await fetch('/api/acmecloud/deploy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ version, service: 'checkout-service' })
      });
      if (res.ok) {
        await refreshStatus();
      }
    } catch (err) {
      console.error('Failed to deploy build:', err);
    } finally {
      setIsDeployingBuild(null);
    }
  };

  const handleToggleTraffic = async () => {
    setIsTogglingTraffic(true);
    try {
      const res = await fetch('/api/acmecloud/traffic/toggle', { method: 'POST' });
      if (res.ok) {
        await refreshStatus();
      }
    } catch (err) {
      console.error('Failed to toggle traffic:', err);
    } finally {
      setIsTogglingTraffic(false);
    }
  };

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
    setCart((prev) => {
      return prev
        .map((item) => {
          if (item.product.id === productId) {
            const newQty = item.quantity + delta;
            return newQty > 0 ? { ...item, quantity: newQty } : null;
          }
          return item;
        })
        .filter(Boolean) as CartItem[];
    });
  };

  const removeFromCart = (productId: string) => {
    setCart((prev) => prev.filter((item) => item.product.id !== productId));
  };

  const subtotal = cart.reduce((acc, item) => acc + item.product.price * item.quantity, 0);
  const tax = Math.round(subtotal * 0.0825);
  const total = subtotal + tax;

  // Checkout execution hitting live backend
  const handleExecuteCheckout = async () => {
    setIsCheckingOut(true);
    setCheckoutResult(null);
    setCheckoutStep('Validating hardware allocations and inventory reservations...');

    try {
      await new Promise((r) => setTimeout(r, 600));
      setCheckoutStep('Dispatching order transaction to checkout-service (port 8001)...');

      const res = await fetch('/api/store/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_id: '00000000-0000-0000-0000-000000000001',
          total_amount: total,
          currency: 'USD',
          items: cart.map((c) => ({
            id: c.product.id,
            name: c.product.name,
            quantity: c.quantity,
            price: c.product.price
          }))
        })
      });

      if (res.ok) {
        const data = await res.json();
        setCheckoutResult({
          status: 'CONFIRMED',
          orderId: data.order_id,
          version: data.version,
          executionMode: data.execution_mode,
          message: data.message,
          warning: data.warning
        });
        setCart([]);
      } else {
        const errData = await res.json().catch(() => ({ detail: 'Service communication fault' }));
        setCheckoutResult({
          status: 'FAILED',
          errorCode: res.status,
          errorDetail: errData.detail || 'HTTP transaction rejected by checkout-service backend.'
        });
      }
    } catch (err: any) {
      setCheckoutResult({
        status: 'FAILED',
        errorCode: 503,
        errorDetail: err.message || 'Network transport failure connecting to checkout-service.'
      });
    } finally {
      setIsCheckingOut(false);
      setCheckoutStep('');
    }
  };

  const filteredProducts =
    selectedCategory === 'All Systems'
      ? PRODUCTS
      : PRODUCTS.filter((p) => p.category === selectedCategory);

  const activeVersion = acmeStatus?.active_version || '2.4.0';
  const isHealthy = acmeStatus?.health?.status === 'HEALTHY';

  return (
    <div className="min-h-screen bg-[#0d0e12] text-[#f4f4f5] flex flex-col font-sans selection:bg-zinc-800 selection:text-white">
      {/* 1. Global Navigation Bar */}
      <header className="h-16 bg-[#121318] border-b border-[#232530] px-4 lg:px-8 flex items-center justify-between sticky top-0 z-30">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-zinc-800 border border-zinc-700 flex items-center justify-center font-mono font-bold text-sm tracking-wider text-white">
              A
            </div>
            <div>
              <div className="text-sm font-semibold tracking-tight text-white flex items-center gap-2">
                <span>ACME HARDWARE & SYSTEMS</span>
                <span className="text-[10px] font-mono uppercase bg-zinc-800 text-zinc-300 px-1.5 py-0.5 rounded border border-zinc-700">
                  Production Store
                </span>
              </div>
              <div className="text-[11px] text-zinc-400 font-mono">
                Port 3002 // Enterprise Hardware Storefront
              </div>
            </div>
          </div>
        </div>

        {/* Center: Category Filter Pills */}
        <div className="hidden md:flex items-center bg-[#171821] border border-[#272938] rounded-lg p-1 text-xs font-mono">
          {['All Systems', 'Compute & AI', 'Storage Arrays', 'Control Terminals'].map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1 rounded-md transition-all cursor-pointer ${
                selectedCategory === cat
                  ? 'bg-zinc-800 text-white font-medium shadow-sm'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Right Nav Utilities */}
        <div className="flex items-center gap-3">
          {/* Active Backend Version Badge */}
          <button
            onClick={() => setIsDevDrawerOpen(true)}
            className={`hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-lg border text-xs font-mono transition-all cursor-pointer ${
              isHealthy
                ? 'bg-emerald-950/30 text-emerald-300 border-emerald-800/50 hover:bg-emerald-900/40'
                : 'bg-red-950/40 text-red-200 border-red-800/60 hover:bg-red-900/50'
            }`}
            title="Click to open DevOps & Chaos Engineering Drawer"
          >
            <span
              className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-emerald-400' : 'bg-red-400 animate-pulse'}`}
            />
            <span>Build: v{activeVersion}</span>
            <span className="text-[10px] uppercase font-bold opacity-75">
              [{isHealthy ? 'Nominal' : 'Fault'}]
            </span>
          </button>

          {/* Cart Trigger */}
          <button
            onClick={() => setIsCartOpen(true)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-white text-xs font-medium transition-all cursor-pointer"
          >
            <ShoppingCart className="w-3.5 h-3.5 text-zinc-300" />
            <span>Cart</span>
            <span className="bg-zinc-900 text-zinc-200 text-[11px] font-mono px-1.5 py-0.2 rounded-full border border-zinc-700">
              {cart.reduce((a, b) => a + b.quantity, 0)}
            </span>
          </button>

          {/* Open Aegis Mission Control Button */}
          <a
            href="http://localhost:3000"
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => {
              if (onOpenAegis && window.location.port !== '3002') {
                e.preventDefault();
                onOpenAegis();
              }
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white text-black hover:bg-zinc-200 text-xs font-semibold tracking-tight transition-all cursor-pointer"
          >
            <Activity className="w-3.5 h-3.5 text-black" />
            <span className="hidden lg:inline">Aegis Mission Control (Port 3000)</span>
            <ExternalLink className="w-3 h-3 text-black/70" />
          </a>
        </div>
      </header>

      {/* 2. Hardware Hero Announcement */}
      <section className="bg-gradient-to-b from-[#15161f] to-[#0d0e12] border-b border-[#232530] px-4 lg:px-8 py-10">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div className="max-w-3xl">
              <div className="flex items-center gap-2 text-xs font-mono text-zinc-400 mb-2">
                <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                <span>Q4 2026 HARDWARE RELEASE // CLUSTER INFRASTRUCTURE</span>
              </div>
              <h1 className="text-3xl lg:text-4xl font-bold tracking-tight text-white mb-3">
                Mission-Critical Compute & Hardware Appliances
              </h1>
              <p className="text-sm text-zinc-400 leading-relaxed max-w-2xl">
                Bare-metal compute, low-latency NVMe arrays, and precision operator gear engineered
                for autonomous infrastructure. Orders are dispatched live through the Acme Checkout
                Service cluster.
              </p>
            </div>

            <div className="bg-[#161722] border border-[#2c2e3f] rounded-xl p-4 min-w-[280px]">
              <div className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider mb-2 flex items-center justify-between">
                <span>Cluster Node Telemetry</span>
                <span className="text-emerald-400 font-bold">LIVE</span>
              </div>
              <div className="space-y-1.5 text-xs font-mono">
                <div className="flex justify-between text-zinc-300">
                  <span className="text-zinc-500">Service:</span>
                  <span>checkout-service</span>
                </div>
                <div className="flex justify-between text-zinc-300">
                  <span className="text-zinc-500">Active Build:</span>
                  <span className="text-white font-bold">v{activeVersion}</span>
                </div>
                <div className="flex justify-between text-zinc-300">
                  <span className="text-zinc-500">5xx Error Rate:</span>
                  <span className={acmeStatus?.health?.error_rate_pct && acmeStatus.health.error_rate_pct > 1 ? 'text-red-400 font-bold' : 'text-emerald-400'}>
                    {acmeStatus?.health?.error_rate_pct ?? 0.1}%
                  </span>
                </div>
                <div className="flex justify-between text-zinc-300">
                  <span className="text-zinc-500">P99 Latency:</span>
                  <span>{acmeStatus?.health?.p99_latency_ms ?? 42} ms</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Product Catalog Grid */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold tracking-tight text-white">Available Inventory</h2>
            <span className="text-xs font-mono text-zinc-400">
              ({filteredProducts.length} specifications available)
            </span>
          </div>
          <div className="text-xs font-mono text-zinc-400 hidden sm:block">
            All systems pre-flashed with secure enclave keys
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredProducts.map((product) => {
            const inCart = cart.find((i) => i.product.id === product.id);

            return (
              <div
                key={product.id}
                className="bg-[#14151b] border border-[#232530] hover:border-[#383a4c] rounded-xl p-5 flex flex-col justify-between transition-all duration-200 group"
              >
                <div>
                  {/* Card Header & Icon */}
                  <div className="flex items-start justify-between gap-3 mb-4">
                    <div className="w-10 h-10 rounded-lg bg-[#1c1e28] border border-[#2f3140] flex items-center justify-center text-zinc-300 group-hover:text-white group-hover:border-zinc-500 transition-colors">
                      {product.iconType === 'cpu' && <Cpu className="w-5 h-5" />}
                      {product.iconType === 'server' && <Server className="w-5 h-5" />}
                      {product.iconType === 'storage' && <HardDrive className="w-5 h-5" />}
                      {product.iconType === 'display' && <Monitor className="w-5 h-5" />}
                      {product.iconType === 'keydeck' && <Terminal className="w-5 h-5" />}
                      {product.iconType === 'clock' && <Zap className="w-5 h-5" />}
                    </div>

                    <div className="flex flex-col items-end">
                      <span className="text-base font-mono font-bold text-white tracking-tight">
                        ${product.price.toLocaleString()}
                      </span>
                      <span className="text-[10px] font-mono uppercase text-zinc-400">
                        {product.stockBadge}
                      </span>
                    </div>
                  </div>

                  {/* Title & Category */}
                  <div className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider mb-1">
                    {product.category}
                  </div>
                  <h3 className="text-base font-semibold text-white tracking-tight mb-2">
                    {product.name}
                  </h3>
                  <p className="text-xs text-zinc-400 leading-relaxed mb-4">
                    {product.description}
                  </p>

                  {/* Hardware Spec Bullets */}
                  <div className="bg-[#181a24] border border-[#262836] rounded-lg p-3 mb-5 space-y-1">
                    {product.specs.map((spec, i) => (
                      <div key={i} className="text-[11px] font-mono text-zinc-300 flex items-center gap-2">
                        <span className="w-1 h-1 rounded-full bg-zinc-500" />
                        <span>{spec}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Card CTA */}
                <div className="pt-2 border-t border-[#1e202b] flex items-center justify-between gap-3">
                  <div className="text-[11px] font-mono text-zinc-400">
                    Lead time: 24h dispatch
                  </div>

                  {inCart ? (
                    <div className="flex items-center gap-2 bg-zinc-800 border border-zinc-700 rounded-lg p-1">
                      <button
                        onClick={() => updateQuantity(product.id, -1)}
                        className="w-6 h-6 flex items-center justify-center rounded bg-zinc-700 hover:bg-zinc-600 text-white cursor-pointer"
                      >
                        <Minus className="w-3 h-3" />
                      </button>
                      <span className="text-xs font-mono font-bold px-1.5 text-white">
                        {inCart.quantity}
                      </span>
                      <button
                        onClick={() => updateQuantity(product.id, 1)}
                        className="w-6 h-6 flex items-center justify-center rounded bg-zinc-700 hover:bg-zinc-600 text-white cursor-pointer"
                      >
                        <Plus className="w-3 h-3" />
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => addToCart(product)}
                      className="px-3.5 py-1.5 rounded-lg bg-white text-black hover:bg-zinc-200 text-xs font-semibold tracking-tight transition-all flex items-center gap-1.5 cursor-pointer active:scale-95"
                    >
                      <ShoppingCart className="w-3.5 h-3.5 text-black" />
                      <span>Add to Cart</span>
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </main>

      {/* 4. Slide-Out Cart & Live Checkout Drawer */}
      {isCartOpen && (
        <div className="fixed inset-0 z-40 flex justify-end">
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
            onClick={() => !isCheckingOut && setIsCartOpen(false)}
          />

          <div className="relative w-full max-w-md bg-[#13141a] border-l border-[#262836] h-full flex flex-col z-10 shadow-2xl">
            {/* Cart Header */}
            <div className="p-5 border-b border-[#232530] flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <ShoppingBag className="w-4 h-4 text-white" />
                <h3 className="text-sm font-semibold text-white tracking-tight">Enterprise Cart</h3>
                <span className="text-xs font-mono text-zinc-400">
                  ({cart.reduce((a, b) => a + b.quantity, 0)} items)
                </span>
              </div>
              <button
                onClick={() => !isCheckingOut && setIsCartOpen(false)}
                className="w-7 h-7 rounded-lg hover:bg-zinc-800 flex items-center justify-center text-zinc-400 hover:text-white cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Cart Items List */}
            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {cart.length === 0 ? (
                <div className="h-64 flex flex-col items-center justify-center text-center p-6 border border-dashed border-zinc-800 rounded-xl">
                  <ShoppingBag className="w-10 h-10 text-zinc-600 mb-3" />
                  <div className="text-sm font-medium text-zinc-300 mb-1">Your cart is empty</div>
                  <div className="text-xs text-zinc-500 mb-4">
                    Select enterprise servers or terminals to initiate an order.
                  </div>
                  <button
                    onClick={() => setIsCartOpen(false)}
                    className="px-3 py-1.5 rounded-lg bg-zinc-800 text-white text-xs font-medium cursor-pointer hover:bg-zinc-700"
                  >
                    Continue Browsing
                  </button>
                </div>
              ) : (
                cart.map((item) => (
                  <div
                    key={item.product.id}
                    className="bg-[#181a24] border border-[#272938] rounded-xl p-3.5 flex flex-col gap-2"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="text-[10px] font-mono uppercase text-zinc-400">
                          {item.product.category}
                        </div>
                        <h4 className="text-xs font-semibold text-white tracking-tight">
                          {item.product.name}
                        </h4>
                      </div>
                      <button
                        onClick={() => removeFromCart(item.product.id)}
                        className="text-zinc-500 hover:text-red-400 p-1 cursor-pointer"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    <div className="flex items-center justify-between pt-2 border-t border-[#222432]">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => updateQuantity(item.product.id, -1)}
                          className="w-5 h-5 flex items-center justify-center rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300 cursor-pointer"
                        >
                          <Minus className="w-2.5 h-2.5" />
                        </button>
                        <span className="text-xs font-mono font-bold text-white px-1">
                          {item.quantity}
                        </span>
                        <button
                          onClick={() => updateQuantity(item.product.id, 1)}
                          className="w-5 h-5 flex items-center justify-center rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300 cursor-pointer"
                        >
                          <Plus className="w-2.5 h-2.5" />
                        </button>
                      </div>

                      <div className="text-right">
                        <div className="text-xs font-mono font-bold text-white">
                          ${(item.product.price * item.quantity).toLocaleString()}
                        </div>
                        <div className="text-[10px] font-mono text-zinc-400">
                          ${item.product.price.toLocaleString()} each
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}

              {/* Order Outcome Display */}
              {checkoutResult && (
                <div
                  className={`mt-4 p-4 rounded-xl border font-mono text-xs ${
                    checkoutResult.status === 'CONFIRMED'
                      ? 'bg-emerald-950/30 border-emerald-800/60 text-emerald-200'
                      : 'bg-red-950/40 border-red-800/60 text-red-200'
                  }`}
                >
                  <div className="flex items-center gap-2 font-bold mb-2">
                    {checkoutResult.status === 'CONFIRMED' ? (
                      <>
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        <span>Order Successfully Confirmed</span>
                      </>
                    ) : (
                      <>
                        <AlertTriangle className="w-4 h-4 text-red-400" />
                        <span>Checkout Transaction Rejected</span>
                      </>
                    )}
                  </div>

                  {checkoutResult.status === 'CONFIRMED' ? (
                    <div className="space-y-1.5 text-[11px]">
                      <div>Order Reference: <strong className="text-white">{checkoutResult.orderId}</strong></div>
                      <div>Backend Engine: <span className="text-white">v{checkoutResult.version} ({checkoutResult.executionMode})</span></div>
                      <div className="text-zinc-300">{checkoutResult.message}</div>
                      {checkoutResult.warning && (
                        <div className="mt-2 p-2 bg-amber-950/40 border border-amber-800/60 text-amber-300 rounded">
                          {checkoutResult.warning}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="space-y-2 text-[11px]">
                      <div className="font-semibold text-red-300">
                        Error HTTP {checkoutResult.errorCode}:
                      </div>
                      <div className="p-2 bg-red-900/30 border border-red-800/40 rounded leading-relaxed text-red-100">
                        {checkoutResult.errorDetail}
                      </div>
                      <div className="text-zinc-300 text-[10px]">
                        The active deployment build (v{activeVersion}) experienced an infrastructure failure.
                      </div>

                      <div className="pt-2 flex flex-col gap-2">
                        <a
                          href="http://localhost:3000"
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => {
                            if (onOpenAegis && window.location.port !== '3002') {
                              e.preventDefault();
                              onOpenAegis();
                            }
                          }}
                          className="w-full py-2 bg-white text-black hover:bg-zinc-200 font-sans font-semibold rounded text-center text-xs flex items-center justify-center gap-1.5"
                        >
                          <Activity className="w-3.5 h-3.5 text-black" />
                          <span>Diagnose in Aegis SRE Mission Control</span>
                        </a>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Cart Footer / Checkout Form */}
            {cart.length > 0 && (
              <div className="p-5 border-t border-[#232530] bg-[#101116] space-y-4">
                <div className="space-y-1.5 text-xs font-mono">
                  <div className="flex justify-between text-zinc-400">
                    <span>Subtotal:</span>
                    <span className="text-white">${subtotal.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between text-zinc-400">
                    <span>Enterprise Freight:</span>
                    <span className="text-emerald-400">COMPLIMENTARY</span>
                  </div>
                  <div className="flex justify-between text-zinc-400">
                    <span>Estimated Tax (8.25%):</span>
                    <span className="text-white">${tax.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between text-sm font-bold text-white pt-2 border-t border-[#232530]">
                    <span>Total Due:</span>
                    <span>${total.toLocaleString()} USD</span>
                  </div>
                </div>

                {isCheckingOut && (
                  <div className="p-3 bg-zinc-900/80 border border-zinc-700 rounded-lg text-xs font-mono text-zinc-300 flex items-center gap-2">
                    <RefreshCw className="w-3.5 h-3.5 animate-spin text-blue-400 shrink-0" />
                    <span>{checkoutStep}</span>
                  </div>
                )}

                <button
                  disabled={isCheckingOut}
                  onClick={handleExecuteCheckout}
                  className="w-full py-2.5 rounded-lg bg-white text-black hover:bg-zinc-200 disabled:opacity-50 text-xs font-bold tracking-tight transition-all flex items-center justify-center gap-2 cursor-pointer shadow-lg active:scale-98"
                >
                  <ShieldCheck className="w-4 h-4 text-black" />
                  <span>{isCheckingOut ? 'Processing Order...' : 'Execute Checkout'}</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 5. Floating / Docked DevOps & Chaos Engineering Drawer */}
      <div className="fixed bottom-4 right-4 z-30">
        {!isDevDrawerOpen ? (
          <button
            onClick={() => setIsDevDrawerOpen(true)}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[#181a24] hover:bg-[#202330] border border-[#2f3242] shadow-2xl text-xs font-mono text-white transition-all cursor-pointer group"
          >
            <Sliders className="w-3.5 h-3.5 text-zinc-400 group-hover:text-white" />
            <span>DevOps & Chaos Lab</span>
            <span
              className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-emerald-400' : 'bg-red-400 animate-pulse'}`}
            />
            <span className="text-[11px] text-zinc-400">v{activeVersion}</span>
          </button>
        ) : (
          <div className="w-[380px] sm:w-[460px] bg-[#14151d] border border-[#2b2e3f] rounded-2xl shadow-2xl overflow-hidden animate-in fade-in slide-in-from-bottom-5 duration-200">
            {/* Drawer Header */}
            <div className="p-4 bg-[#181a24] border-b border-[#282a3a] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sliders className="w-4 h-4 text-white" />
                <span className="text-xs font-bold tracking-tight text-white uppercase font-mono">
                  DevOps & Chaos Simulation Lab
                </span>
              </div>
              <button
                onClick={() => setIsDevDrawerOpen(false)}
                className="w-6 h-6 rounded flex items-center justify-center text-zinc-400 hover:text-white hover:bg-zinc-800 cursor-pointer"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Drawer Body */}
            <div className="p-4 max-h-[70vh] overflow-y-auto space-y-4 text-xs font-mono">
              {/* Build status summary */}
              <div className="bg-[#1a1c27] border border-[#2d3043] rounded-xl p-3 space-y-1.5">
                <div className="flex justify-between items-center text-zinc-400">
                  <span>Target Cluster:</span>
                  <span className="text-white font-bold">checkout-service</span>
                </div>
                <div className="flex justify-between items-center text-zinc-400">
                  <span>Current Build:</span>
                  <span className={`font-bold ${isHealthy ? 'text-emerald-400' : 'text-red-400'}`}>
                    v{activeVersion} [{isHealthy ? 'Nominal' : 'Fault'}]
                  </span>
                </div>
                <div className="flex justify-between items-center text-zinc-400">
                  <span>Pool Limit:</span>
                  <span className="text-white">{activeVersion === '2.4.1' ? '5 (Starved)' : '25 (Nominal)'}</span>
                </div>
              </div>

              {/* Synthetic Traffic Generator */}
              <div className="flex items-center justify-between bg-[#191b26] border border-[#2c2f42] rounded-xl p-3">
                <div>
                  <div className="text-xs font-semibold text-white">Synthetic Traffic Generator</div>
                  <div className="text-[10px] text-zinc-400">Injects 45 rps background customer load</div>
                </div>
                <button
                  disabled={isTogglingTraffic}
                  onClick={handleToggleTraffic}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                    acmeStatus?.traffic_running
                      ? 'bg-amber-950/60 border border-amber-700 text-amber-200 hover:bg-amber-900/60'
                      : 'bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-300'
                  }`}
                >
                  {acmeStatus?.traffic_running ? (
                    <>
                      <Square className="w-3 h-3 fill-amber-300 text-amber-300" />
                      <span>Stop Traffic</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-3 h-3 fill-zinc-300 text-zinc-300" />
                      <span>Start Traffic</span>
                    </>
                  )}
                </button>
              </div>

              {/* 5 Deployable Builds */}
              <div>
                <div className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider mb-2">
                  Select Build to Deploy ({builds.length} available)
                </div>
                <div className="space-y-2">
                  {builds.map((b) => {
                    const isCurrent = activeVersion === b.version;
                    const isDeploying = isDeployingBuild === b.version;

                    return (
                      <div
                        key={b.version}
                        className={`p-3 rounded-xl border transition-all ${
                          isCurrent
                            ? b.status === 'STABLE'
                              ? 'bg-emerald-950/30 border-emerald-700/80 text-emerald-100'
                              : 'bg-red-950/30 border-red-700/80 text-red-100'
                            : 'bg-[#181a24] border-[#292b3a] hover:border-[#3d4057]'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-white">v{b.version}</span>
                            <span
                              className={`text-[9px] uppercase px-1.5 py-0.2 rounded font-bold ${
                                b.status === 'STABLE'
                                  ? 'bg-emerald-900/60 text-emerald-300 border border-emerald-700'
                                  : 'bg-red-900/60 text-red-300 border border-red-700'
                              }`}
                            >
                              {b.scenario}
                            </span>
                          </div>

                          {isCurrent ? (
                            <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider">
                              [Active Now]
                            </span>
                          ) : (
                            <button
                              disabled={isDeploying || isDeployingBuild !== null}
                              onClick={() => handleDeployBuild(b.version)}
                              className="px-2.5 py-1 bg-white text-black hover:bg-zinc-200 disabled:opacity-50 rounded text-[11px] font-bold cursor-pointer"
                            >
                              {isDeploying ? 'Deploying...' : 'Deploy'}
                            </button>
                          )}
                        </div>

                        <div className="text-[11px] text-zinc-300 mb-1">{b.name}</div>
                        <div className="text-[10px] text-zinc-400">
                          Expected 5xx Error: <span className="text-zinc-200">{b.expected_error_rate}</span> | DB Pool: {b.pool_max}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Direct Link to Aegis SRE Mission Control */}
              <div className="pt-2 border-t border-[#282a3a]">
                <a
                  href="http://localhost:3000"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-white font-sans text-xs font-semibold flex items-center justify-center gap-1.5 transition-all"
                >
                  <Activity className="w-3.5 h-3.5 text-white" />
                  <span>Launch Aegis Autonomous SRE Copilot (Port 3000)</span>
                  <ExternalLink className="w-3 h-3 text-zinc-400" />
                </a>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
