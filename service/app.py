from flask import Flask, request, jsonify, render_template_string
import os
import qrcode
import io
import base64
from service.mixing_service import MixingService
from service.fee_model import default_tiers, quote

app = Flask(__name__)
service = MixingService()

HTML_INDEX = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ABCMint MIX_PROTOCOL // V.1.0</title>
    <style>
        :root {
            --term-green: #00ff41;
            --term-dim: #008F11;
            --term-bg: #000000;
            --term-panel: rgba(0, 20, 0, 0.85);
            --term-glow: 0 0 10px rgba(0, 255, 65, 0.4);
            --term-border: 1px solid var(--term-green);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Courier New', Courier, monospace;
            background-color: var(--term-bg);
            color: var(--term-green);
            height: 100%;
            margin: 0;
            overflow-y: auto; /* Always allow scroll, handled by height:100% on html/body */
            position: relative;
        }
        html { min-height: 100vh;
            overflow-y: scroll !important; /* Force scrollbar strictly */
            position: relative;
        }
        canvas#matrix {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
        }
        .scanline {
            width: 100%;
            height: 100px;
            z-index: 9999;
            background: linear-gradient(0deg, rgba(0,0,0,0) 0%, rgba(0, 255, 65, 0.04) 50%, rgba(0,0,0,0) 100%);
            opacity: 0.1;
            position: fixed; /* Changed from absolute to fixed */
            left: 0;
            top: -100px; /* Start above screen */
            animation: scanline 10s linear infinite;
            pointer-events: none;
        }
        @keyframes scanline {
            0% { top: -100px; }
            100% { top: 100%; }
        }
        .container {
            background: var(--term-panel);
            border: 1px solid var(--term-green);
            box-shadow: 0 0 20px rgba(0, 255, 65, 0.2);
            max-width: 600px;
            width: 95%;
            margin: 40px auto;
            padding: 30px;
            position: relative;
            backdrop-filter: blur(3px);
        }
        .container::before {
            content: "SYSTEM_READY";
            position: absolute;
            top: -10px;
            left: 20px;
            background: var(--term-bg);
            padding: 0 10px;
            font-size: 12px;
            color: var(--term-green);
            border: 1px solid var(--term-green);
        }
        .container::after {
            content: "";
            position: absolute;
            bottom: -5px;
            right: -5px;
            width: 20px;
            height: 20px;
            border-bottom: 2px solid var(--term-green);
            border-right: 2px solid var(--term-green);
        }
        
        .logo { text-align: center; margin-bottom: 20px; }
        .logo img { 
            width: 80px; 
            height: 80px; 
            border: 1px solid var(--term-green);
            filter: grayscale(100%) sepia(100%) hue-rotate(90deg) saturate(300%) brightness(0.8) contrast(1.2);
            box-shadow: var(--term-glow);
        }
        
        h1 {
            text-align: center;
            font-size: 24px;
            margin-bottom: 30px;
            text-transform: uppercase;
            letter-spacing: 2px;
            text-shadow: 0 0 5px var(--term-green);
            border-bottom: 1px dashed var(--term-dim);
            padding-bottom: 10px;
        }
        
        .form-group { margin-bottom: 20px; }
        label {
            display: block;
            margin-bottom: 5px;
            font-size: 14px;
            text-transform: uppercase;
        }
        
        input[type="number"], input[type="text"], select {
            width: 100%;
            background: black;
            border: 1px solid var(--term-dim);
            color: var(--term-green);
            padding: 12px;
            font-family: 'Courier New', Courier, monospace;
            font-size: 16px;
            transition: all 0.3s;
        }
        input:focus, select:focus {
            outline: none;
            border-color: var(--term-green);
            box-shadow: var(--term-glow);
            background: #001100;
        }
        
        input:disabled, select:disabled, button:disabled, fieldset:disabled input, fieldset:disabled select {
            background: #111 !important;
            color: #555 !important;
            border-color: #333 !important;
            cursor: not-allowed !important;
            box-shadow: none !important;
        }
        
        .quote {
            border: 1px dashed var(--term-green);
            padding: 15px;
            margin: 20px 0;
            font-size: 13px;
            background: rgba(0, 20, 0, 0.5);
        }
        .quote div { margin-bottom: 5px; }
        .quote span { color: #fff; text-shadow: 0 0 2px #fff; }
        
        .md-button {
            width: 100%;
            padding: 15px;
            background: transparent;
            border: 1px solid var(--term-green);
            color: var(--term-green);
            font-family: 'Courier New', Courier, monospace;
            font-size: 16px;
            font-weight: bold;
            text-transform: uppercase;
            cursor: pointer;
            transition: all 0.2s;
            position: relative;
            overflow: hidden;
        }
        .md-button:hover {
            background: var(--term-green);
            color: black;
            box-shadow: var(--term-glow);
        }
        .md-button:disabled {
            border-color: var(--term-dim);
            color: var(--term-dim);
            cursor: not-allowed;
            background: transparent;
            box-shadow: none;
        }
        .md-button.outlined {
            border: 1px dashed var(--term-green);
        }
        .md-button.outlined:hover {
            background: rgba(0, 255, 65, 0.1);
            color: var(--term-green);
        }
        
        .result {
            margin-top: 30px;
            border-top: 2px solid var(--term-green);
            padding-top: 20px;
            animation: glitch 0.5s ease-out;
        }
        @keyframes glitch {
            0% { opacity: 0; transform: translateX(-10px); }
            20% { opacity: 1; transform: translateX(10px); }
            40% { transform: translateX(-5px); }
            60% { transform: translateX(5px); }
            100% { transform: translateX(0); }
        }
        
        .qrcode {
            text-align: center;
            margin: 20px 0;
            padding: 15px;
            border: 1px dotted var(--term-green);
            background: black;
        }
        #qrcode {
            display: inline-block;
            padding: 10px;
            background: white; /* QR needs contrast */
            border: 2px solid var(--term-green);
        }
        
        .status {
            margin-top: 20px;
            padding: 15px;
            background: rgba(0, 20, 0, 0.8);
            border-left: 3px solid var(--term-green);
        }
        .status h3 {
            border-bottom: 1px solid var(--term-dim);
            padding-bottom: 5px;
            margin-bottom: 10px;
            font-size: 16px;
        }
        .indicator {
            padding: 2px 6px;
            font-size: 11px;
            border: 1px solid;
            margin-left: 5px;
        }
        .indicator.ok { border-color: var(--term-green); color: var(--term-green); }
        .indicator.warn { border-color: red; color: red; text-shadow: 0 0 2px red; }
        
        .tx-link {
            margin: 5px 0;
            font-size: 12px;
            padding-left: 10px;
            border-left: 1px solid var(--term-dim);
        }
        .tx-link a {
            color: var(--term-green);
            text-decoration: none;
            opacity: 0.8;
        }
        .tx-link a:hover {
            text-decoration: underline;
            opacity: 1;
            text-shadow: var(--term-glow);
        }
        
        /* Custom Scrollbar */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: black; }
        ::-webkit-scrollbar-thumb { background: var(--term-dim); border: 1px solid black; }
        ::-webkit-scrollbar-thumb:hover { background: var(--term-green); }

        @media (max-width: 600px) {
            .container { width: 100%; margin: 0; border: none; }
        }
    </style>
</head>
<body>
    <canvas id="matrix"></canvas>
    <div class="scanline"></div>
    
    <div class="container">
        <div class="logo">
            <img id="logo" src="/static/logo.png" onerror="this.src='https://trae-api-us.mchost.guru/api/ide/v1/text_to_image?prompt=metallic%20white%20silver%20stylized%20R%20monogram%20with%20chrome%203D%20effect%2C%20sapphire%20blue%20gemstone%20background%2C%20liquid%20glass%20finish%2C%20high%20gloss%20beveled%20edges%2C%20professional%20crypto%20logo%20design%2C%20transparent%20background&image_size=square_hd'" alt="ABCMint Logo">
        </div>
        <div style="text-align:right; font-size:12px; margin-bottom:10px; border-bottom:1px dotted var(--term-dim); padding-bottom:5px;">
            <span style="margin-right:15px;">>> DIFF: <span id="difficulty" class="indicator">...</span></span>
            <span style="margin-right:15px;">>> PEERS: <span id="peerCount" class="indicator">...</span></span>
            >> BLOCK_HEIGHT: <span id="blockHeight" class="indicator">SYNCING...</span>
        </div>
        <h1>ABCMint MIX_PROTOCOL</h1>
        
        <form id="mixForm">
            <fieldset id="mixFieldSet" style="border:none; padding:0; margin:0;">
            <div class="form-group">
                <label>>> INPUT_AMOUNT:</label>
                <input type="number" id="amount" step="1" min="1" required placeholder="_">
            </div>
            <div class="form-group">
                <label>>> TARGET_NODE:</label>
                <input type="text" id="targetAddress" required placeholder="_">
            </div>
            <div class="form-group">
                <label>>> SECURITY_LEVEL:</label>
                <select id="tier"></select>
            </div>
            </fieldset>
            
            <div class="quote" id="quoteBox" style="display:none;">
                <div>[CALC] SERVICE_FEE: <span id="feePercent">0</span>% / <span id="absFee">0</span> ABCMint</div>
                <div>[CALC] MINER_FEE: <span id="minerFee">0</span> ABCMint</div>
                <div>[EST] TX_COUNT: <span id="txCount">0</span></div>
                <div>[EST] NET_OUTPUT: <span id="netAmount">0</span> ABCMint</div>
                <div>[INFO] CAP_STRATEGY: MAX_MINER <span id="minerCap">0</span> | OVERFLOW <span id="extraService">0</span></div>
                <div>[SRC] FEE_MODEL: <span id="feeSource">UNKNOWN</span></div>
            </div>
            
            <button type="submit" class="md-button">[ INITIALIZE_MIXING_SEQUENCE ]</button>
        </form>
        
        <div id="result" style="display:none;">
            <h2 style="text-align:center; margin-bottom:15px; border-bottom:1px solid var(--term-green)">// OPERATION_STATUS</h2>
            
            <div class="quote" style="border-style:dotted; margin-bottom:15px;">
                <div style="color:var(--term-dim); font-size:10px; margin-bottom:5px;">>> MISSION_PARAMETERS</div>
                <div>TARGET: <span id="infoTarget" style="color:white;"></span></div>
                <div>AMOUNT: <span id="infoAmount" style="color:white;"></span> ABCMint</div>
            </div>

            <div class="qrcode">
                <p>>> DEPOSIT_REQUIRED: <span id="displayAmount"></span> ABCMint</p>
                <div id="qrcode"></div>
                <p style="font-size:10px; margin-top:5px;">ADDR: <span id="depositAddress"></span></p>
                <p>>> DETECTED: <span id="receivedAmount">0</span> / <span id="requiredAmount">0</span></p>
                <p>>> THRESHOLD: <span id="depositStatus" class="indicator warn">PENDING</span></p>
                <p style="font-size:10px; color:var(--term-dim)">NOTE: INCLUDES <span id="depositMinerFee">0</span> FEE</p>
            </div>
            
            <div class="status">
                <h3>>> SYSTEM_LOG</h3>
                <p>STATUS: <span id="status">WAITING</span></p>
                <p>CONFIRMATIONS: <span id="confirmations">0</span></p>
                <p>STEP_1_READY: <span id="mixReady">FALSE</span></p>
                <p style="font-size:11px; color:var(--term-dim); word-break:break-all;">INTERNAL_MIX_NODE: <span id="mixAddr">-</span></p>
                <p>SHARD_READY: <span id="shardReady">0</span></p>
                <p>DEP_CONF: <span id="depositConf">0</span></p>
                <p style="color:red">ERROR: <span id="errText"></span></p>
                <div id="txids" style="margin-top:10px; font-family:'Courier New';"></div>
                
                <button id="resetBtn" class="md-button outlined" style="display:none; margin-top:15px;">[ SYSTEM_RESET ]</button>
            </div>
        </div>
    </div>

    <script>
        // Matrix Rain Effect
        const canvas = document.getElementById('matrix');
        const ctx = canvas.getContext('2d');

        function resizeCanvas() {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        }
        // window.addEventListener('resize', resizeCanvas); // Disable auto-resize to prevent layout thrashing
        resizeCanvas();

        const alphabet = '01';

        const fontSize = 20;
        const columns = canvas.width/fontSize;

        const rainDrops = [];
        for( let x = 0; x < columns; x++ ) {
            rainDrops[x] = 1;
        }

        const draw = () => {
            ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            ctx.fillStyle = '#0F0';
            ctx.font = fontSize + 'px monospace';

            for(let i = 0; i < rainDrops.length; i++)
            {
                const text = alphabet.charAt(Math.floor(Math.random() * alphabet.length));
                ctx.fillText(text, i*fontSize, rainDrops[i]*fontSize);

                if(rainDrops[i]*fontSize > canvas.height && Math.random() > 0.975){
                    rainDrops[i] = 0;
                }
                rainDrops[i]++;
            }
        };
        setInterval(draw, 105);

        // App Logic
        let jobId = localStorage.getItem('mixJobId') || null;
        let lastDepositAddr = localStorage.getItem('lastDepositAddr') || null;
        let pollInterval = null;
        let lastConf = -1;
        let stuckCount = 0;
        let lastDeposit = -1;
        let depositStuck = 0;

        async function loadTiers() {
            const res = await fetch('/api/mix/tiers');
            const data = await res.json();
            const sel = document.getElementById('tier');
            sel.innerHTML = '';
            const opts = data.tiers || [];
            opts.forEach((t) => {
                const o = document.createElement('option');
                o.value = `${t.shards}:${t.hops}`;
                o.textContent = `[LVL] ${t.name} (SHARD:${t.shards}/HOP:${t.hops})`;
                sel.appendChild(o);
            });
            updateQuote();
        }
        async function updateQuote() {
            const amount = document.getElementById('amount').value || '0';
            let shards, hops;
            const tier = document.getElementById('tier').value;
            if(!tier) return;
            const parts = tier.split(':');
            shards = parseInt(parts[0]);
            hops = parseInt(parts[1]);
            if (!amount || parseFloat(amount) <= 0) { document.getElementById('quoteBox').style.display = 'none'; return; }
            const res = await fetch('/api/mix/quote', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({amount, shards, hops}) });
            const q = await res.json();
            if (q.error) return;
            document.getElementById('quoteBox').style.display = 'block';
            document.getElementById('feePercent').textContent = (q.percent * 100).toFixed(2);
            document.getElementById('absFee').textContent = q.abs_fee.toFixed(8);
            document.getElementById('minerFee').textContent = q.miner_fee.toFixed(8);
            document.getElementById('txCount').textContent = q.tx_count;
            document.getElementById('netAmount').textContent = q.net_amount.toFixed(8);
            if (typeof q.cap === 'number') document.getElementById('minerCap').textContent = q.cap.toFixed(8);
            if (typeof q.extra_to_service === 'number') document.getElementById('extraService').textContent = q.extra_to_service.toFixed(8);
            if (q.fee_source) document.getElementById('feeSource').textContent = (q.fee_source === 'node' ? 'NODE_RPC' : 'STATIC_CONST');
        }
        document.getElementById('amount').addEventListener('input', updateQuote);
        document.getElementById('tier').addEventListener('change', updateQuote);
        loadTiers();
        resumeJob();
        
        // System Status Poll
        async function updateSystemStatus() {
            try {
                const res = await fetch('/api/system/status');
                const data = await res.json();
                const el = document.getElementById('blockHeight');
                const elPeer = document.getElementById('peerCount');
                const elDiff = document.getElementById('difficulty');
                
                if (data.blockHeight) {
                    el.textContent = data.blockHeight;
                    el.className = 'indicator ok';
                } else {
                    el.textContent = 'OFFLINE';
                    el.className = 'indicator warn';
                }

                if (typeof data.peerCount === 'number') {
                    elPeer.textContent = data.peerCount;
                    elPeer.className = 'indicator ok';
                } else {
                    elPeer.textContent = '0';
                    elPeer.className = 'indicator warn';
                }

                if (typeof data.difficulty === 'number') {
                    elDiff.textContent = data.difficulty;
                    elDiff.className = 'indicator ok';
                } else {
                    elDiff.textContent = '0';
                    elDiff.className = 'indicator warn';
                }
            } catch(e) {
                const el = document.getElementById('blockHeight');
                el.textContent = 'CONN_ERR';
                el.className = 'indicator warn';
            }
        }
        setInterval(updateSystemStatus, 10000);
        updateSystemStatus();

        document.getElementById('mixForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            // STRICT CHECK: If job is already running, do absolutely nothing.
            if (jobId) {
                console.log('Job already active, ignoring submit.');
                return;
            }
            
            // Immediately disable button to prevent double-click
            const submitBtn = document.querySelector('#mixForm button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.textContent = '[ PROCESSING... ]';
            
            // Immediately disable inputs via fieldset
            document.getElementById('mixFieldSet').disabled = true;

            const amount = document.getElementById('amount').value;
            const targetAddress = document.getElementById('targetAddress').value;
            const tier = document.getElementById('tier').value;
            let shards, hops;
            const parts = tier.split(':');
            shards = parseInt(parts[0]);
            hops = parseInt(parts[1]);
            const res = await fetch('/api/mix/request', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({amount: amount, targetAddress, shards, hops}) });
            const data = await res.json();
            if (data.error) { 
                // Show error but DO NOT UNLOCK. User must click RESET.
                document.getElementById('result').style.display = 'block';
                document.getElementById('status').textContent = 'INIT_FAILED';
                document.getElementById('errText').textContent = data.error;
                
                // Show reset button to allow user to start over
                const rBtn = document.getElementById('resetBtn');
                if (rBtn) rBtn.style.display = 'inline-block';
                
                // Keep button disabled but update text
                submitBtn.textContent = '[ SYSTEM_HALTED ]';
                
                // IMPORTANT: KEEP FIELDSET DISABLED. 
                // User must click RESET to re-enable.
                return; 
            }
            jobId = data.jobId;
            localStorage.setItem('mixJobId', jobId);
            localStorage.setItem('mixTarget', targetAddress);
            localStorage.setItem('mixAmount', amount);
            
            document.getElementById('infoTarget').textContent = targetAddress;
            document.getElementById('infoAmount').textContent = amount;
            
            document.getElementById('displayAmount').textContent = Number(data.depositRequired || amount).toFixed(8);
            document.getElementById('depositAddress').textContent = data.depositAddress;
            document.getElementById('result').style.display = 'block';
            
            // Force a small delay to ensure DOM is rendered before QR generation and button visibility
            setTimeout(() => {
                const qrelem = document.getElementById('qrcode'); 
                qrelem.innerHTML = ''; 
                new QRCode(qrelem, data.depositAddress);
                
                // Explicitly show reset button here to ensure it appears
                const rBtn = document.getElementById('resetBtn');
                if (rBtn) rBtn.style.display = 'inline-block';
            }, 50);

            document.getElementById('feePercent').textContent = (data.feePercent * 100).toFixed(2);
            document.getElementById('absFee').textContent = Number(data.absFee || 0).toFixed(8);
            document.getElementById('minerFee').textContent = Number(data.minerFee || 0).toFixed(8);
            const hintMiner = document.getElementById('depositMinerFee'); if (hintMiner) hintMiner.textContent = Number(data.minerFee || 0).toFixed(8);
            document.getElementById('txCount').textContent = data.txCount || 0;
            document.getElementById('netAmount').textContent = Number(data.netAmount || 0).toFixed(8);
            document.getElementById('quoteBox').style.display = 'block';
            if (typeof data.minerFeeCap === 'number') document.getElementById('minerCap').textContent = Number(data.minerFeeCap).toFixed(8);
            if (typeof data.extraServiceFee === 'number') document.getElementById('extraService').textContent = Number(data.extraServiceFee).toFixed(8);
            if (typeof data.depositExtra === 'number') document.getElementById('depositExtra').textContent = Number(data.depositExtra).toFixed(8);
            if (data.feeSource) document.getElementById('feeSource').textContent = (data.feeSource === 'node' ? 'NODE_RPC' : 'STATIC_CONST');
            document.getElementById('requiredAmount').textContent = Number(data.depositRequired || amount).toFixed(8);
            
            lastDepositAddr = data.depositAddress; localStorage.setItem('lastDepositAddr', lastDepositAddr);
            disableForm();
            
            // Poll immediately once, then interval
            pollStatusFunction(); 
            pollStatus();
        });
        async function safeResume() {
            if (!jobId) return;
            try { await fetch('/api/mix/resume', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({jobId})}); } catch(e) {}
        }

        async function resumeJob() {
            if (!jobId) return;
            const res = await fetch(`/api/mix/status?jobId=${jobId}`);
            const data = await res.json();
            if (data && !data.error) {
                document.getElementById('result').style.display = 'block';
                
                // Restore info from localStorage or backend if available (backend doesn't always return target in status, so use local as fallback)
                const savedTarget = localStorage.getItem('mixTarget') || '---';
                const savedAmount = localStorage.getItem('mixAmount') || '---';
                document.getElementById('infoTarget').textContent = savedTarget;
                document.getElementById('infoAmount').textContent = savedAmount;

                document.getElementById('depositAddress').textContent = data.depositAddress || lastDepositAddr || '';
                const req = typeof data.depositRequired === 'number' ? data.depositRequired : 0;
                document.getElementById('requiredAmount').textContent = req ? req : '';
                document.getElementById('displayAmount').textContent = req ? Number(req).toFixed(8) : '';
                const qrelem = document.getElementById('qrcode'); qrelem.innerHTML = '';
                if (data.depositAddress) { new QRCode(qrelem, data.depositAddress); lastDepositAddr = data.depositAddress; localStorage.setItem('lastDepositAddr', lastDepositAddr); }
                else if (lastDepositAddr) { new QRCode(qrelem, lastDepositAddr); }
                const hintMiner = document.getElementById('depositMinerFee'); if (hintMiner && typeof data.minerFee === 'number') hintMiner.textContent = Number(data.minerFee).toFixed(8);
                disableForm();
                pollStatus();
            } else {
                document.getElementById('result').style.display = 'block';
                document.getElementById('status').textContent = 'RECOVERING...';
                await safeResume();
                disableForm();
                pollStatus();
            }
        }
        function disableForm() {
            document.getElementById('mixFieldSet').disabled = true;
            document.querySelector('#mixForm button[type="submit"]').disabled = true;
            document.querySelector('#mixForm button[type="submit"]').textContent = '[ SEQUENCE_RUNNING ]';
            const resetBtn = document.getElementById('resetBtn'); resetBtn.style.display = 'inline-block';
        }
        function clearJob() {
            localStorage.removeItem('mixJobId'); 
            localStorage.removeItem('mixTarget');
            localStorage.removeItem('mixAmount');
            jobId = null;
            document.getElementById('mixFieldSet').disabled = false;
            const submitBtn = document.querySelector('#mixForm button[type="submit"]');
            submitBtn.disabled = false;
            submitBtn.textContent = '[ INITIALIZE_MIXING_SEQUENCE ]';
            document.getElementById('resetBtn').style.display = 'none';
        }
        document.getElementById('resetBtn').addEventListener('click', () => { clearJob(); location.reload(); });
        async function pollStatus() {
            if (pollInterval) clearInterval(pollInterval);
            pollInterval = setInterval(pollStatusFunction, 5000);
        }
        
        async function pollStatusFunction() {
                if (!jobId) return;
                // Always ensure reset button is visible when polling
                const rBtn = document.getElementById('resetBtn');
                if (rBtn && rBtn.style.display === 'none') rBtn.style.display = 'inline-block';

                const res = await fetch(`/api/mix/status?jobId=${jobId}`);
                const data = await res.json();
                if (data.error) {
                    await safeResume();
                    document.getElementById('status').textContent = 'RECOVERING...';
                    document.getElementById('resetBtn').style.display = 'inline-block';
                }
                // Always update status display regardless of deposit status
                document.getElementById('status').textContent = translateStatus(data.status);
                document.getElementById('confirmations').textContent = data.confirmations;
                if (typeof data.mixUtxoReady === 'boolean') document.getElementById('mixReady').textContent = data.mixUtxoReady ? 'YES' : 'NO';
                if (data.mixAddress) document.getElementById('mixAddr').textContent = data.mixAddress;
                if (typeof data.shardReadyCount === 'number') document.getElementById('shardReady').textContent = data.shardReadyCount;
                document.getElementById('errText').textContent = (data.status === 'completed') ? '' : (data.error ? String(data.error) : '');
                if (typeof data.depositConfirmations === 'number') document.getElementById('depositConf').textContent = data.depositConfirmations;
                if (typeof data.depositReceived === 'number') { document.getElementById('receivedAmount').textContent = data.depositReceived.toFixed(8); }
                if (typeof data.depositRequired === 'number') { document.getElementById('requiredAmount').textContent = data.depositRequired; }
                const recv = parseFloat(document.getElementById('receivedAmount').textContent) || 0;
                const reqd = parseFloat(document.getElementById('requiredAmount').textContent) || 0;
                const meets = recv >= reqd && reqd > 0;
                const ds = document.getElementById('depositStatus'); ds.textContent = meets ? 'READY' : 'PENDING'; ds.className = 'indicator ' + (meets ? 'ok' : 'warn');
                const txDiv = document.getElementById('txids'); txDiv.innerHTML = '';
                // QR fallback
                try {
                    const qrelem = document.getElementById('qrcode');
                    if (qrelem && qrelem.childNodes.length === 0 && (data.depositAddress || lastDepositAddr)) {
                        new QRCode(qrelem, data.depositAddress || lastDepositAddr);
                    }
                } catch(e) {}
                // Transaction Display - Cyberpunk Style
                if (data.txid1) {
                    txDiv.innerHTML += `<div class="tx-link">[STEP_1] MIX_INIT: <a href="https://abcscan.io/#/Transactionpage?data=${data.txid1}" target="_blank">${data.txid1.substring(0,20)}...</a></div>`;
                }
                
                const fanouts = Array.isArray(data.shardTxidsFanout) ? data.shardTxidsFanout : [];
                if (fanouts.length > 0) {
                    txDiv.innerHTML += `<div class="tx-link">[STEP_2] SHARD_FANOUT (${fanouts.length}):</div>`;
                    for (const f of fanouts) {
                        txDiv.innerHTML += `<div class="tx-link">  -> <a href="https://abcscan.io/#/Transactionpage?data=${f}" target="_blank">${f.substring(0,20)}...</a></div>`;
                    }
                }

                const hops = Array.isArray(data.shardTxidsHops) ? data.shardTxidsHops : [];
                let hopCount = 0;
                for (const hl of hops) { if (Array.isArray(hl)) hopCount += hl.length; }
                if (hopCount > 0) {
                    txDiv.innerHTML += `<div class="tx-link">[STEP_3] OBFUSCATION_HOPS (${hopCount}):</div>`;
                    for (const hl of hops) {
                        if (!Array.isArray(hl)) continue;
                        for (const h of hl) {
                            txDiv.innerHTML += `<div class="tx-link">  -> <a href="https://abcscan.io/#/Transactionpage?data=${h}" target="_blank">${h.substring(0,20)}...</a></div>`;
                        }
                    }
                }

                const finals = Array.isArray(data.shardTxidsFinal) ? data.shardTxidsFinal : [];
                if (finals.length > 0) {
                    txDiv.innerHTML += `<div class="tx-link">[FINAL] TARGET_DELIVERY (${finals.length}):</div>`;
                    for (const t of finals) {
                        txDiv.innerHTML += `<div class="tx-link">  >> <a href="https://abcscan.io/#/Transactionpage?data=${t}" target="_blank">${t.substring(0,20)}...</a></div>`;
                    }
                } else if (data.txid2) {
                    txDiv.innerHTML += `<div class="tx-link">[STEP_2] EXEC: <a href="https://abcscan.io/#/Transactionpage?data=${data.txid2}" target="_blank">${data.txid2}</a></div>`;
                }
                
                if (data.status === 'waiting_confirmations') {
                    const c = Number(data.confirmations||0);
                    if (c === lastConf) stuckCount++; else { stuckCount = 0; lastConf = c; }
                    if (stuckCount >= 5) {
                        try { await fetch('/api/mix/resume', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({jobId})}); } catch(e) {}
                        stuckCount = 0;
                    }
                }
                if (data.status === 'waiting_deposit') {
                    const r = typeof data.depositReceived === 'number' ? data.depositReceived : -1;
                    if (r === lastDeposit) depositStuck++; else { depositStuck = 0; lastDeposit = r; }
                    if (depositStuck >= 10) {
                        try { await fetch('/api/mix/resume', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({jobId})}); } catch(e) {}
                        depositStuck = 0;
                    }
                }
                if (data.status === 'completed' || data.status === 'error') { clearInterval(pollInterval); }
        }
        function translateStatus(status) {
            const map = { 
                'pending': 'PENDING_INIT', 
                'waiting_deposit': 'AWAITING_FUNDS', 
                'deposit_received': 'FUNDS_DETECTED', 
                'mixing_step1': 'EXEC_PHASE_1', 
                'waiting_confirmations': 'CONFIRMING_PHASE_1', 
                'mixing_step2': 'EXEC_PHASE_2', 
                'completed': 'SEQUENCE_COMPLETE', 
                'error': 'SYSTEM_FAILURE' 
            };
            return map[status] || status.toUpperCase();
        }
    </script>
    <script src="https://cdn.jsdelivr.net/npm/qrcodejs@1.0.0/qrcode.min.js"></script>
    </body>
    </html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_INDEX)

from decimal import Decimal

@app.route('/api/mix/request', methods=['POST'])
def mix_request():
    data = request.get_json()
    if not data or 'amount' not in data or 'targetAddress' not in data:
        return jsonify({'error': 'Missing amount or targetAddress'}), 400
    
    try:
        amount = Decimal(str(data['amount']))
        target_address = data['targetAddress']
        shards = int(data.get('shards', 0)) or int(os.environ.get('TIER_STANDARD_SHARDS', '3'))
        hops = int(data.get('hops', 0)) or int(os.environ.get('TIER_STANDARD_HOPS', '1'))
        if amount <= Decimal('0'):
            return jsonify({'error': 'Amount must be positive'}), 400
        
        job = service.create_job(target_address, amount, shards, hops)
        return jsonify({
            'jobId': job.job_id,
            'depositAddress': job.deposit_address,
            'amount': float(job.amount),
            'shards': job.shard_count,
            'hops': job.hop_count,
            'feePercent': float(job.fee_percent),
            'absFee': float(job.abs_fee),
            'minerFee': float(job.miner_fee),
            'txCount': job.tx_count,
            'netAmount': float(job.net_amount),
            'depositRequired': float(job.deposit_required),
            'minerFeeCap': float(os.environ.get('MINER_FEE_CAP', '1')),
            'extraServiceFee': float(getattr(job, 'extra_service_fee', Decimal('0.0'))),
            'depositExtra': float(os.environ.get('DEPOSIT_EXTRA', '0.1')),
            'feeSource': service.iface.get_fee_source_hint()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mix/status')
def mix_status():
    job_id = request.args.get('jobId')
    if not job_id:
        return jsonify({'error': 'Missing jobId'}), 400
    
    job = service.get_job(job_id)
    if not job:
        # Try reloading state from disk in case backend created it
        service._load_state()
        job = service.get_job(job_id)
        if not job:
            return jsonify({'error': 'Job not found'}), 404

    # Force sync from disk if status seems stuck (backend might have updated it)
    if job.status in ('waiting_deposit', 'error', 'mixing_step1', 'waiting_confirmations', 'mixing_step2'):
        service._load_state()
        job = service.get_job(job_id)

    # Double Check Completion: If backend says mixing_step2 but we have final txids, it's completed.
    # Or if status is stuck but funds arrived at target (complex to check without knowing target balance before).
    # We rely on shardTxidsFinal being populated.
    if job.status != 'completed' and job.shard_txids_final and len(job.shard_txids_final) >= job.shard_count:
        job.status = 'completed'
        service._save_state()

    mix_ready = False
    shard_ready_count = 0
    deposit_conf = 0
    try:
        minconf2 = int(os.environ.get('MINCONF_STEP2', '6'))
        minconf_shard = int(os.environ.get('MINCONF_SHARD', '0'))
        if job.mix_address:
            mix_ready = bool(service.iface.listunspent_for_addresses([job.mix_address], minconf=minconf2))
        fan_txs = set(getattr(job, 'shard_txids_fanout', []) or [])
        if fan_txs:
            all_u = service.iface.listunspent(minconf=minconf_shard) or []
            shard_ready_count = sum(1 for u in all_u if u.get('txid') in fan_txs and Decimal(str(u.get('amount', 0))) > 0)
        if job.deposit_address:
            du = service.iface.listunspent_for_addresses([job.deposit_address], minconf=0) or []
            if du:
                try:
                    deposit_conf = max(int(u.get('confirmations', 0)) for u in du)
                except Exception:
                    deposit_conf = 0
    except Exception:
        pass

    # Fix display lag: Actively query RPC for the latest confirmations
    if job.txid1 and job.status == 'waiting_confirmations':
        try:
            tx_info = service.iface._rpc('gettransaction', [job.txid1])
            if tx_info:
                job.confirmations = int(tx_info.get('confirmations', 0))
        except Exception:
            pass
            
    # Fix stuck status: If UI sees deposit confirmed but status is stale, hint UI to poll aggressively
    # or rely on backend to catch up. We rely on 'depositConfirmations' field in JSON.

    # Recovery Patch: If deposit spent but txid1 missing (crash recovery)
    if not job.txid1 and job.deposit_address:
        try:
            # Check if balance is 0 but received > required
            u = service.iface.listunspent_for_addresses([job.deposit_address], minconf=0)
            if not u:
                recv = Decimal(str(service.iface._rpc('getreceivedbyaddress', [job.deposit_address, 0])))
                if recv >= job.deposit_required:
                    # Deposit spent! Find the spending tx.
                    txs = service.iface._rpc('listtransactions', ["*", 100])
                    for tx in reversed(txs):
                        tid = tx.get('txid')
                        if tid:
                            try:
                                raw = service.iface._rpc('getrawtransaction', [tid, 1])
                                for vin in raw.get('vin', []):
                                    prev_txid = vin.get('txid')
                                    prev_vout = vin.get('vout')
                                    if prev_txid:
                                        prev = service.iface._rpc('getrawtransaction', [prev_txid, 1])
                                        if prev and 'vout' in prev:
                                            p_out = prev['vout'][prev_vout]
                                            if job.deposit_address in p_out['scriptPubKey'].get('addresses', []):
                                                # Found it!
                                                job.txid1 = tid
                                                # Check if we are already completed (check if final shard txs exist in history)
                                                # If we find final txs sending to target_address, we can jump to completed.
                                                # This is a bit expensive, but worth it for recovery.
                                                try:
                                                    recent_txs = service.iface._rpc('listtransactions', ["*", 50])
                                                    final_txs = []
                                                    for rt in recent_txs:
                                                        if rt.get('category') == 'send' and rt.get('address') == job.target_address:
                                                            final_txs.append(rt.get('txid'))
                                                    
                                                    if len(final_txs) >= job.shard_count:
                                                        job.shard_txids_final = final_txs
                                                        job.status = 'completed'
                                                        job.txid2 = final_txs[0] # Show one of them
                                                    elif job.status == 'waiting_deposit':
                                                        job.status = 'waiting_confirmations'
                                                except Exception:
                                                    if job.status == 'waiting_deposit':
                                                        job.status = 'waiting_confirmations'
                                                
                                                service._save_state()
                                                break
                                if job.txid1: break
                            except Exception:
                                pass
        except Exception:
            pass

    # Populate final shard txids proactively to ensure UI focuses on mix progress
    try:
        if job.target_address:
            recent = service.iface._rpc('listtransactions', ["*", 200]) or []
            finals_scan = []
            for rt in recent:
                addr = rt.get('address')
                cat = rt.get('category')
                tid = rt.get('txid')
                if tid and addr == job.target_address and cat in ('send', 'receive'):
                    finals_scan.append(tid)
            # de-duplicate preserving order
            seen = set()
            finals_scan = [t for t in finals_scan if not (t in seen or seen.add(t))]
            if finals_scan:
                job.shard_txids_final = finals_scan
                if not job.txid2:
                    job.txid2 = finals_scan[-1]
                # If enough finals exist, mark completed
                if job.status != 'completed' and len(finals_scan) >= max(1, int(job.shard_count)):
                    job.status = 'completed'
                service._save_state()
    except Exception:
        pass

    return jsonify({
        'status': job.status,
        'confirmations': job.confirmations,
        'depositAddress': job.deposit_address,
        'depositReceived': float(job.deposit_received),
        'depositRequired': float(job.deposit_required),
        'shards': job.shard_count,
        'hops': job.hop_count,
        'feePercent': float(job.fee_percent),
        'absFee': float(job.abs_fee),
        'minerFee': float(job.miner_fee),
        'txCount': job.tx_count,
        'netAmount': float(job.net_amount),
        'shardProgressTotal': getattr(job, 'shard_progress_total', 0),
        'shardProgressCompleted': getattr(job, 'shard_progress_completed', 0),
        'shardTxidsFanout': getattr(job, 'shard_txids_fanout', []),
        'shardTxidsHops': getattr(job, 'shard_txids_hops', []),
        'shardTxidsFinal': getattr(job, 'shard_txids_final', []),
        'fanoutCount': len(getattr(job, 'shard_txids_fanout', []) or []),
        'hopTxCount': sum(len(x) for x in (getattr(job, 'shard_txids_hops', []) or []) if isinstance(x, list)),
        'finalTxCount': len(getattr(job, 'shard_txids_final', []) or []),
        'txid1': job.txid1,
        'txid2': job.txid2,
        'error': job.error,
        'mixUtxoReady': mix_ready,
        'mixAddress': job.mix_address,
        'shardReadyCount': shard_ready_count,
        'depositConfirmations': deposit_conf
    })

@app.route('/api/mix/tiers')
def mix_tiers():
    return jsonify({'tiers': default_tiers()})

@app.route('/api/mix/resume', methods=['POST'])
def mix_resume():
    data = request.get_json() or {}
    job_id = data.get('jobId') or request.args.get('jobId')
    if not job_id:
        return jsonify({'error': 'Missing jobId'}), 400
    ok = service.resume_job(job_id)
    if not ok:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify({'ok': True})

@app.route('/api/mix/quote', methods=['POST'])
def mix_quote():
    data = request.get_json()
    if not data or 'amount' not in data or 'shards' not in data or 'hops' not in data:
        return jsonify({'error': 'Missing amount/shards/hops'}), 400
    try:
        amount = Decimal(str(data['amount']))
        shards = int(data['shards'])
        hops = int(data['hops'])
        q = quote(amount, shards, hops)
        # Convert decimals to float for JSON serialization
        q_out = {k: (float(v) if isinstance(v, Decimal) else v) for k, v in q.items()}
        
        try:
            q_out['fee_source'] = service.iface.get_fee_source_hint()
        except Exception:
            q_out['fee_source'] = 'constant'
        return jsonify(q_out)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/system/status')
def system_status():
    try:
        height = service.iface._rpc('getblockcount')
        peers = service.iface._rpc('getpeerinfo')
        peer_count = len(peers) if isinstance(peers, list) else 0
        diff_val = service.iface._rpc('getdifficulty')
        if not isinstance(diff_val, (int, float, Decimal)):
            diff_val = 0
        difficulty = int(diff_val)
        return jsonify({'blockHeight': height, 'peerCount': peer_count, 'difficulty': difficulty})
    except Exception as e:
        return jsonify({'error': str(e), 'blockHeight': 0, 'peerCount': 0, 'difficulty': 0}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)