from __future__ import annotations

from graphviz import Digraph

class CargaHoraria:
    def __init__(self, teorica: int, pratica: int):
        self.teorica = teorica
        self.pratica = pratica
        self.total = self.teorica + self.pratica

class Disciplina:
    def __init__(self, codigo: str, nome: str, periodo: int, carga_horaria: CargaHoraria):
        self.codigo = codigo
        self.nome = nome
        self.periodo = periodo
        self.carga_horaria = carga_horaria

        self.prerequisitos = []
        self.corequisitos = []

    def __str__(self):
        return '%s - %s' % (
            self.codigo,
            self.nome,
        )

class Curso:
    def __init__(self, nome: str, disciplinas: [Disciplina]):
        self.nome = nome
        self.disciplinas = disciplinas
    
    def perfil_curricular_dot(self):
        dot = Digraph('Perfil Curricular %s' % self.nome)
        dot.attr(labelloc='t', label='Perfil Curricular de %s' % self.nome)
        dot.attr(rankdir='LR', splines='ortho')

        ultimo_periodo = max(map(lambda disciplina: disciplina.periodo, self.disciplinas))
        for i in range(1, ultimo_periodo+2):
            disciplinas = filter(lambda disciplina: disciplina.periodo == i-1, self.disciplinas)
            with dot.subgraph() as s:
                s.attr(rank='same')
                s.node(str(i), shape='none')
                if i > 1:
                    dot.edge(str(i-1), str(i), dir='none')
                for disciplina in disciplinas:
                    s.node(disciplina.codigo, '%s\n%s' % (disciplina.codigo, disciplina.nome), shape='box', width='3.5')
                    for prerequisito in disciplina.prerequisitos:
                        dot.edge(disciplina.codigo, prerequisito.codigo, constraint='true')
        
        return dot
    
    def __getitem__(self, codigo: str):
        for disciplina in self.disciplinas:
            if disciplina.codigo == codigo:
                return disciplina
        
        raise KeyError('%s não tem %s como disciplina' % (self.nome, codigo))