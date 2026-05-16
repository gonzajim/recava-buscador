import React from 'react';
import {
  ShieldCheck,
  Search,
  Scale,
  FileCheck,
  BarChart3,
  Clock,
  ArrowRight,
  CheckCircle2,
  Lock,
  Briefcase,
  Users,
  ClipboardCheck,
  UploadCloud,
  Layers,
  FileSearch,
  CheckSquare
} from 'lucide-react';

const Landing = ({ onLoginClick }) => {
  const processSteps = [
    {
      title: "Carga de Documento",
      desc: "Suba el PDF del informe de sostenibilidad (EINF/CSRD).",
      icon: <UploadCloud className="w-8 h-8 text-blue-600" />
    },
    {
      title: "Selección de Indicadores",
      desc: "Use la matriz estándar o cargue sus propios criterios.",
      icon: <Layers className="w-8 h-8 text-indigo-600" />
    },
    {
      title: "Búsqueda de Evidencias",
      desc: "Nuestra IA localiza párrafos literales y páginas exactas.",
      icon: <FileSearch className="w-8 h-8 text-emerald-600" />
    },
    {
      title: "Validación Experta",
      desc: "Revise y confirme los hallazgos con un clic.",
      icon: <CheckSquare className="w-8 h-8 text-amber-600" />
    }
  ];

  const features = [
    {
      title: "Rigor en la Evidencia",
      desc: "Análisis exhaustivo basado exclusivamente en el texto del informe, eliminando riesgos de interpretación.",
      icon: <Scale className="w-6 h-6 text-blue-600" />
    },
    {
      title: "Matrices Dinámicas",
      desc: "Adapte el análisis a sus necesidades cargando sus propias matrices de indicadores.",
      icon: <ClipboardCheck className="w-6 h-6 text-indigo-600" />
    },
    {
      title: "Citas Literales",
      desc: "Cada hallazgo incluye el párrafo literal y la página real para una trazabilidad total.",
      icon: <Search className="w-6 h-6 text-emerald-600" />
    },
    {
      title: "Eficiencia Analítica",
      desc: "Diseñado para ahorrar cientos de horas de búsqueda manual en documentos extensos.",
      icon: <Users className="w-6 h-6 text-amber-600" />
    }
  ];

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-900">
      {/* Navegación */}
      <nav className="sticky top-0 z-50 bg-white/90 backdrop-blur-md border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-blue-700 p-2 rounded-lg shadow-blue-200 shadow-lg">
              <ShieldCheck className="text-white w-6 h-6" />
            </div>
            <div>
              <span className="font-bold text-xl block leading-none text-slate-900">RECAVA</span>
              <span className="text-xs font-semibold text-blue-600 tracking-widest uppercase">Análisis de Evidencias</span>
            </div>
          </div>
          <div className="hidden md:flex gap-10 text-sm font-semibold text-slate-600">
            <a href="#proceso" className="hover:text-blue-700 transition-colors">Cómo funciona</a>
            <a href="#beneficios" className="hover:text-blue-700 transition-colors">Beneficios</a>
          </div>
          <button
            onClick={onLoginClick}
            className="bg-slate-900 text-white px-6 py-2.5 rounded-lg text-sm font-bold hover:bg-slate-800 transition-all shadow-md flex items-center gap-2">
            Acceso Analizador
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </nav>

      {/* Hero Section Reestructurada */}
      <section className="relative pt-20 pb-32 overflow-hidden bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="text-center max-w-4xl mx-auto">
            <div className="inline-flex items-center gap-2 bg-emerald-50 border border-emerald-100 px-4 py-1.5 rounded-full text-emerald-700 text-xs font-bold mb-8 tracking-wide">
              <Lock className="w-3 h-3" /> TECNOLOGÍA DE EXTRACCIÓN DE EVIDENCIAS (V3.2)
            </div>
            <h1 className="text-5xl md:text-7xl font-black text-slate-900 mb-8 leading-[1.1]">
              Análisis y Búsqueda de <br />
              <span className="text-blue-700 text-6xl md:text-8xl">Evidencias AI</span>
            </h1>
            <p className="text-xl text-slate-600 mb-12 max-w-2xl mx-auto leading-relaxed">
              Deje de buscar manualmente en informes de cientos de páginas. 
              Localice evidencias exactas para sus indicadores NEIS y CSRD con rigor documental.
            </p>

            {/* BOTÓN PRINCIPAL MUY EVIDENTE */}
            <div className="flex justify-center mb-20">
              <button
                onClick={onLoginClick}
                className="group relative bg-blue-700 text-white px-12 py-6 rounded-2xl font-black text-2xl hover:bg-blue-800 transition-all shadow-[0_20px_50px_rgba(29,78,216,0.3)] hover:shadow-[0_20px_60px_rgba(29,78,216,0.5)] hover:-translate-y-1 flex items-center gap-4">
                Analizar documento
                <ArrowRight className="w-8 h-8 group-hover:translate-x-2 transition-transform" />
              </button>
            </div>
          </div>

          {/* Gráfico de Pasos (Visual) */}
          <div id="proceso" className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-12">
            {processSteps.map((step, index) => (
              <div key={index} className="relative p-8 bg-slate-50 rounded-3xl border border-slate-100 flex flex-col items-center text-center">
                <div className="mb-6 p-4 bg-white rounded-2xl shadow-sm border border-slate-100">
                  {step.icon}
                </div>
                <h3 className="font-bold text-slate-900 mb-2">{step.title}</h3>
                <p className="text-sm text-slate-500 leading-relaxed">{step.desc}</p>
                {index < 3 && (
                  <div className="hidden lg:block absolute top-1/2 -right-4 translate-x-1/2 -translate-y-1/2 z-20">
                    <ArrowRight className="w-6 h-6 text-slate-300" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Elemento Decorativo */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full opacity-5 pointer-events-none">
          <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-blue-600 rounded-full blur-[180px]"></div>
          <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-emerald-600 rounded-full blur-[150px]"></div>
        </div>
      </section>

      {/* Características Secundarias */}
      <section id="beneficios" className="py-24 bg-slate-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-slate-900 mb-4">¿Por qué usar Recava Analizador?</h2>
            <p className="text-slate-500">Un asistente de alto nivel diseñado para profesionales que exigen precisión.</p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((f, i) => (
              <div key={i} className="group bg-white p-8 rounded-3xl border border-slate-200 hover:border-blue-300 transition-all shadow-sm">
                <div className="mb-6 p-4 rounded-2xl bg-slate-50 w-fit group-hover:bg-blue-600 group-hover:text-white transition-colors text-slate-700">
                  {f.icon}
                </div>
                <h3 className="font-bold text-xl mb-3 text-slate-900">{f.title}</h3>
                <p className="text-slate-500 text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center gap-8 text-slate-500 text-sm">
          <div className="flex items-center gap-3">
            <ShieldCheck className="text-blue-700 w-6 h-6" />
            <span className="font-bold text-slate-900 text-lg">RECAVA Analizador AI</span>
          </div>
          <div className="text-center md:text-right">
            <p className="mb-2">© 2024 Observatorio de Sostenibilidad.</p>
            <p className="text-xs">Tecnología de análisis de evidencias para informes de sostenibilidad.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Landing;

