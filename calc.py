import math

def calcChiSquareTableVal(colTotal, rowTotal):
    total = rowTotal * colTotal
    tableVal = total/1565
    print(tableVal)


def getSum(listArr):
    tempVal = 0
    for val in listArr:
        tempVal=tempVal+val
        
    print(tempVal)
    

totalSum = [] 

def calcChiSquare(obVal, expVal):
    subtractingChi = obVal - expVal
    subtractingChiSqr = subtractingChi ** 2
    finalCol = subtractingChiSqr/expVal
    totalSum.append(finalCol)
    print(obVal, "___", expVal, "___", f"{subtractingChi:.2f}", "___", f"{subtractingChiSqr:.2f}", "___", f"{finalCol:.2f}")
    print("-----------------------------------------------------------------")
    
# calcChiSquare(18, 11.7)
# calcChiSquare(36, 27)
# calcChiSquare(21, 25.2)
# calcChiSquare(9, 16.2)
# calcChiSquare(6, 9.9)

# calcChiSquare(12, 19.5)
# calcChiSquare(36, 45)
# calcChiSquare(45, 42)
# calcChiSquare(36, 27)
# calcChiSquare(21, 16.5)

# calcChiSquare(6, 3.9)
# calcChiSquare(9, 9)
# calcChiSquare(9, 8.4)
# calcChiSquare(3, 5.4)
# calcChiSquare(3, 3.3)

# calcChiSquare(3, 3.9)
# calcChiSquare(9, 9)
# calcChiSquare(9, 8.4)
# calcChiSquare(6, 5.4)
# calcChiSquare(3, 3.3)

# getSum(totalSum)

mean1=[11.5,13.17]
mean2=[30, 19.5]

def calculateClustering(point, mean):
    x1, y1 = point
    x2, y2 = mean
    distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    print(f"{distance:.2f}")
    print("---------------------")

calculateClustering([7,11],mean1)
calculateClustering([7,11],mean2)
print("done1")

calculateClustering([16,20],mean1)
calculateClustering([16,20],mean2)
print("done2")

calculateClustering([28, 26],mean1)
calculateClustering([28, 26],mean2)
print("done3")

calculateClustering([18,10],mean1)
calculateClustering([18,10],mean2)
print("done4")

calculateClustering([13,19],mean1)
calculateClustering([13,19],mean2)
print("done5")

calculateClustering([22, 29],mean1)
calculateClustering([22, 29],mean2)
print("done6")

calculateClustering([32,21],mean1)
calculateClustering([32,21],mean2)
print("done7")

calculateClustering([12,15],mean1)
calculateClustering([12,15],mean2)
print("done8")

calculateClustering([38,2],mean1)
calculateClustering([38,2],mean2)
print("done9")

calculateClustering([3,4],mean1)
calculateClustering([3,4],mean2)
print("done10")


