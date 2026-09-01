\# Core Comparison Predicates



amount\_over(amount,threshold)

amount\_not\_over(amount,threshold)

amount\_at\_least(amount,threshold)

amount\_equals(amount,threshold)



\# Tax Predicates



has\_taxable\_income(individual,taxable\_income)

tax\_amount\_equals(individual,tax\_amount)



\# Filing Status / Schedule Predicates



is\_individual(individual)

is\_married\_individual(individual)

is\_surviving\_spouse(individual)

is\_head\_of\_household(individual)

makes\_joint\_return(individual,spouse)



qualifies\_for\_joint\_return\_tax\_schedule(individual)

qualifies\_for\_head\_of\_household\_tax\_schedule(individual)

qualifies\_for\_unmarried\_tax\_schedule(individual)

qualifies\_for\_separate\_return\_tax\_schedule(individual)



\# Employment / Employer Predicates



qualifies\_as\_employer(employer,calendar\_year)

has\_individuals\_in\_employ(employer,individual,calendar\_year)

employment\_tax\_context\_applies(employer,calendar\_year)

total\_wages\_paid\_with\_respect\_to\_employment(employer,total\_wages,calendar\_year,employment)

excise\_tax\_imposed(employer,calendar\_year)

excise\_tax\_amount(employer,calendar\_year,tax\_amount)



\# Wages / Remuneration Predicates



paid\_wages(person,wages,calendar\_year)

paid\_cash\_wages(person,wages,calendar\_year)

paid\_agricultural\_wages(person,wages,calendar\_year)

paid\_domestic\_service\_cash\_wages(person,wages,calendar\_year)

