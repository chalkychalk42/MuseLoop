document.addEventListener('alpine:init', () => {
  Alpine.data('dashboard', () => ({
    // State
    jobs: [],
    selectedJob: null,
    skills: [],
    wsConnected: false,
    view: 'list', // 'list' | 'detail'

    // Form
    form: {
      task: '',
      style: '',
      max_iterations: 5,
      quality_threshold: 0.7,
    },

    // WebSocket
    ws: null,

    async init() {
      await this.fetchJobs();
      await this.fetchSkills();
      this.connectWs();
      // Refresh jobs periodically
      setInterval(() => this.fetchJobs(), 5000);
    },

    connectWs() {
      const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
      this.ws = new WebSocket(`${proto}//${location.host}/ws`);

      this.ws.onopen = () => { this.wsConnected = true; };
      this.ws.onclose = () => {
        this.wsConnected = false;
        // Reconnect after 3s
        setTimeout(() => this.connectWs(), 3000);
      };
      this.ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data);
          this.handleWsEvent(msg.event, msg.data);
        } catch (e) {
          console.error('WS parse error:', e);
        }
      };
    },

    handleWsEvent(event, data) {
      // Update job in list
      if (data.job_id) {
        const idx = this.jobs.findIndex(j => j.job_id === data.job_id);
        if (idx >= 0) {
          if (event === 'iteration_start') {
            this.jobs[idx].iteration = data.iteration || 0;
            this.jobs[idx].status = 'running';
          } else if (event === 'iteration_complete') {
            this.jobs[idx].score = data.score || 0;
            this.jobs[idx].best_score = data.best_score || 0;
          } else if (event === 'job_finished') {
            Object.assign(this.jobs[idx], data);
          }
        }
        // Update detail view if watching this job
        if (this.selectedJob && this.selectedJob.job_id === data.job_id) {
          this.fetchJobDetail(data.job_id);
        }
      }
    },

    async fetchJobs() {
      try {
        const res = await fetch('/api/jobs');
        this.jobs = await res.json();
      } catch (e) {
        console.error('Failed to fetch jobs:', e);
      }
    },

    async fetchSkills() {
      try {
        const res = await fetch('/api/skills');
        this.skills = await res.json();
      } catch (e) {
        console.error('Failed to fetch skills:', e);
      }
    },

    async fetchJobDetail(jobId) {
      try {
        const res = await fetch(`/api/jobs/${jobId}`);
        this.selectedJob = await res.json();
      } catch (e) {
        console.error('Failed to fetch job:', e);
      }
    },

    async submitJob() {
      if (!this.form.task.trim()) return;
      try {
        const res = await fetch('/api/jobs', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.form),
        });
        const job = await res.json();
        this.jobs.push(job);
        this.form.task = '';
        this.form.style = '';
      } catch (e) {
        console.error('Failed to submit job:', e);
      }
    },

    async approveJob(jobId, approved) {
      try {
        await fetch(`/api/jobs/${jobId}/approve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ approved, notes: '' }),
        });
        await this.fetchJobDetail(jobId);
      } catch (e) {
        console.error('Failed to approve job:', e);
      }
    },

    selectJob(job) {
      this.selectedJob = job;
      this.view = 'detail';
      this.fetchJobDetail(job.job_id);
    },

    backToList() {
      this.selectedJob = null;
      this.view = 'list';
    },

    progressPct(job) {
      if (!job.max_iterations) return 0;
      return Math.round((job.iteration / job.max_iterations) * 100);
    },

    formatScore(score) {
      return (score || 0).toFixed(2);
    },
  }));
});
