"""Balanced transportation problem on the offline road metric."""
from functools import lru_cache
import numpy as np
from scipy.optimize import linprog
from sklearn.tree import DecisionTreeRegressor
from .roads import CITIES, road


def simplex(supply,demand,distances):
    n,m = distances.shape
    constraints = np.vstack([np.repeat(np.eye(n),m,axis=1),np.tile(np.eye(m),n)])
    result = linprog(distances.ravel(),A_eq=constraints,b_eq=[*supply,*demand],bounds=(0,None),method="highs-ds")
    if not result.success:
        raise ValueError("Симплекс не нашёл допустимый план")
    return np.rint(result.x).astype(int).reshape(n,m)


def features(supply,demand,km):
    return [[km[i,j],km[i,j]-km[i].min(),km[i,j]-km[:,j].min(),
             supply[i]/sum(supply),demand[j]/sum(demand)] for i,j in np.ndindex(km.shape)]


@lru_cache(maxsize=1)
def learned_policy():
    rng = np.random.default_rng(104)
    inputs, labels = [], []
    for _ in range(180):
        cities = rng.permutation(list(CITIES))
        km = np.array([[road(a,b)[0] for b in cities[3:]] for a in cities[:3]])
        supply = rng.integers(1,21,3)
        demand = rng.multinomial(sum(supply)-3,[1/3]*3)+1
        teacher = simplex(supply,demand,km)
        inputs.extend(features(supply,demand,km))
        labels.extend(teacher.ravel()/np.minimum.outer(supply,demand).ravel())
    return DecisionTreeRegressor(max_depth=6,random_state=104).fit(inputs,labels)


def allocate(stock,needs,mode):
    for side in (stock,needs):
        if not side or any(c not in CITIES or type(v) is not int or not 1<=v<=1000000 for c,v in side.items()):
            raise ValueError("Нужны известные города и положительные целые объёмы до миллиона")
    if sum(stock.values())!=sum(needs.values()):
        raise ValueError("Сумма запасов должна равняться сумме потребностей")
    sources,targets=list(stock),list(needs)
    supply,demand=list(stock.values()),list(needs.values())
    km=np.array([[road(a,b)[0] for b in targets] for a in sources])
    if mode=="simplex":
        plan=simplex(supply,demand,km)
    elif mode=="ai":
        scores=learned_policy().predict(features(supply,demand,km)).reshape(km.shape)
        plan=np.zeros_like(km)
        left,right=supply.copy(),demand.copy()
        for i,j in sorted(np.ndindex(km.shape),key=lambda ij:(-scores[ij],km[ij])):
            quantity=min(left[i],right[j])
            plan[i,j]=quantity
            left[i]-=quantity
            right[j]-=quantity
    else:
        raise ValueError("Неизвестный метод")
    if list(plan.sum(axis=0))!=demand or list(plan.sum(axis=1))!=supply or (plan<0).any():
        raise ValueError("План нарушает баланс")
    rows=[]
    for i,j in np.ndindex(km.shape):
        if plan[i,j]:
            length,path=road(sources[i],targets[j])
            rows.append([" → ".join(path),int(plan[i,j]),length])
    return dict(rows=rows,work=int((km*plan).sum()),method=mode)